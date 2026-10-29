from odoo import _, api, fields, models
from odoo.exceptions import UserError


class FmsFuelCost(models.Model):
    _name = 'fms.fuel.cost'
    _description = 'Fuel Cost Log'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(string='Reference', default='New', copy=False, readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('billed', 'Billed'),
    ], string='Status', default='draft', copy=False, tracking=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Supplier / Fuel Station', required=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
    line_ids = fields.One2many('fms.fuel.cost.line', 'cost_id', string='Fuel Details', copy=True)
    total_quantity = fields.Float(string='Total Liters', compute='_compute_totals', store=True)
    total_cost = fields.Monetary(string='Total Cost', compute='_compute_totals', store=True,
                                 currency_field='currency_id')
    notes = fields.Text(string='Notes')
    bill_ids = fields.One2many('account.move', 'fuel_cost_id', string='Vendor Bills')
    bill_count = fields.Integer(string='Bills', compute='_compute_bill_count')

    @api.depends('line_ids.quantity', 'line_ids.total_cost')
    def _compute_totals(self):
        for rec in self:
            rec.total_quantity = sum(rec.line_ids.mapped('quantity'))
            rec.total_cost = sum(rec.line_ids.mapped('total_cost'))

    @api.depends('bill_ids')
    def _compute_bill_count(self):
        for rec in self:
            rec.bill_count = len(rec.bill_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'New':
                seq = self.env['ir.sequence'].sudo()
                ref = seq.next_by_code('fms.fuel.cost')
                if not ref:
                    seq.create({
                        'name': 'Fuel Cost',
                        'code': 'fms.fuel.cost',
                        'prefix': 'FUEL/%(year)s/',
                        'padding': 5,
                    })
                    ref = seq.next_by_code('fms.fuel.cost')
                vals['name'] = ref or 'New'
        return super().create(vals_list)

    # ---- Buttons ----
    def action_confirm(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError(_("Add at least one fuel detail line before confirming."))
            rec.state = 'confirmed'

    def action_reset_draft(self):
        for rec in self:
            if rec.bill_ids.filtered(lambda b: b.state != 'cancel'):
                raise UserError(_("You cannot reset to draft while active vendor bills exist."))
            rec.state = 'draft'

    def action_create_vendor_bill(self):
        self.ensure_one()
        if self.state != 'confirmed':
            raise UserError(_("Confirm the fuel cost before creating a vendor bill."))
        invoice_lines = []
        for line in self.line_ids:
            vals = {
                'name': line.description,
                'quantity': line.quantity,
                'price_unit': line.unit_price,
            }
            if line.account_id:
                vals['account_id'] = line.account_id.id
            if line.analytic_account_id:
                vals['analytic_distribution'] = {str(line.analytic_account_id.id): 100}
            invoice_lines.append((0, 0, vals))
        self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': self.date,
            'ref': self.name,
            'invoice_origin': self.name,
            'fuel_cost_id': self.id,
            'invoice_line_ids': invoice_lines,
        })
        self.state = 'billed'
        return self.action_view_bills()

    def action_view_bills(self):
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Vendor Bills'),
            'res_model': 'account.move',
            'domain': [('fuel_cost_id', '=', self.id)],
            'context': {'default_move_type': 'in_invoice'},
        }
        if len(self.bill_ids) == 1:
            action.update({'view_mode': 'form', 'res_id': self.bill_ids.id})
        else:
            action.update({'view_mode': 'list,form'})
        return action


class FmsFuelCostLine(models.Model):
    _name = 'fms.fuel.cost.line'
    _description = 'Fuel Cost Line'

    cost_id = fields.Many2one('fms.fuel.cost', string='Fuel Cost', required=True, ondelete='cascade')
    currency_id = fields.Many2one('res.currency', related='cost_id.currency_id', readonly=True)
    description = fields.Char(string='Description', required=True)
    quantity = fields.Float(string='Fuel Quantity (Liters)', default=0.0)
    unit_price = fields.Monetary(string='Unit Price', currency_field='currency_id')
    total_cost = fields.Monetary(string='Total Cost', compute='_compute_total_cost', store=True,
                                 currency_field='currency_id')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    account_id = fields.Many2one(
        'account.account', string='Expense Account',
        help="Optional. If empty, the default account of the Vendor Bills journal is used.")

    @api.depends('quantity', 'unit_price')
    def _compute_total_cost(self):
        for line in self:
            line.total_cost = line.quantity * line.unit_price
