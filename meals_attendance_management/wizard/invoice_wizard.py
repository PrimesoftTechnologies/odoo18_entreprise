from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.misc import format_date


class MealsInvoiceWizard(models.TransientModel):
    _name = 'meals.invoice.wizard'
    _description = 'Generate Customer Meals Invoice'

    customer_id = fields.Many2one('res.partner', string='Customer', required=True,
                                  domain=[('is_meal_customer', '=', True)])
    date_from = fields.Date(required=True, default=lambda s: fields.Date.today().replace(day=1))
    date_to = fields.Date(required=True, default=fields.Date.context_today)
    invoice_date = fields.Date(default=fields.Date.context_today)
    group_by_department = fields.Boolean(
        string='One invoice line per department', default=False,
        help="Otherwise one invoice line per meal type.")
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id')
    billable_count = fields.Integer(string='Meals to Invoice', compute='_compute_preview')
    billable_amount = fields.Monetary(string='Amount to Invoice', compute='_compute_preview',
                                      currency_field='currency_id')

    def _get_lines(self):
        self.ensure_one()
        if not (self.customer_id and self.date_from and self.date_to):
            return self.env['meals.attendance.line']
        return self.env['meals.attendance.line'].search([
            ('customer_id', '=', self.customer_id.id),
            ('company_id', '=', self.company_id.id),
            ('date', '>=', self.date_from), ('date', '<=', self.date_to),
            ('state', '=', 'confirmed'), ('attended', '=', True), ('invoice_id', '=', False),
        ])

    @api.depends('customer_id', 'date_from', 'date_to', 'company_id')
    def _compute_preview(self):
        for wiz in self:
            lines = wiz._get_lines()
            wiz.billable_count = len(lines)
            wiz.billable_amount = sum(lines.mapped('amount'))

    def action_create_invoice(self):
        self.ensure_one()
        if self.date_from > self.date_to:
            raise UserError(_("'Date From' must be before 'Date To'."))
        lines = self._get_lines()
        if not lines:
            raise UserError(_("No confirmed, un-invoiced attendance found for this customer and period."))

        groups = defaultdict(lambda: self.env['meals.attendance.line'])
        for line in lines:
            dept = line.department_id.id if self.group_by_department else False
            groups[(line.meal_type_id.id, line.unit_price, dept)] |= line

        period = "%s - %s" % (format_date(self.env, self.date_from), format_date(self.env, self.date_to))
        invoice_lines = []
        for (meal_type_id, price, dept_id), glines in sorted(groups.items(), key=lambda kv: kv[0][0]):
            meal = self.env['meals.type'].browse(meal_type_id)
            label = meal.name
            if dept_id:
                label += " - %s" % self.env['hr.department'].browse(dept_id).name
            invoice_lines.append((0, 0, {
                'name': "%s (%s)" % (label, period),
                'quantity': len(glines),
                'price_unit': price,
            }))

        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.customer_id.id,
            'invoice_date': self.invoice_date,
            'invoice_origin': _("Meals %s", period),
            'company_id': self.company_id.id,
            'invoice_line_ids': invoice_lines,
        })
        lines.write({'invoice_id': move.id})
        return {
            'type': 'ir.actions.act_window', 'res_model': 'account.move',
            'res_id': move.id, 'view_mode': 'form', 'target': 'current',
        }
