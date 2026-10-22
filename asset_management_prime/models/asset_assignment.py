from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class AssetAssignment(models.Model):
    _name = 'asset.assignment'
    _description = 'Asset Assignment (Check-out / Check-in)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_from desc, id desc'

    name = fields.Char('Reference', default='New', copy=False, readonly=True)
    asset_id = fields.Many2one('asset.asset', required=True, tracking=True, index=True,
                               domain="[('state', 'in', ('available', 'in_use'))]")
    company_id = fields.Many2one('res.company', required=True,
                                 default=lambda self: self.env.company)
    employee_id = fields.Many2one('hr.employee', string='Assigned To', required=True,
                                  tracking=True, index=True)
    department_id = fields.Many2one('hr.department', compute='_compute_department',
                                    store=True, readonly=False)
    location_id = fields.Many2one('asset.location', string='Location')
    assignment_type = fields.Selection([
        ('permanent', 'Permanent'), ('temporary', 'Temporary Loan')],
        default='permanent', required=True, tracking=True)
    date_from = fields.Datetime('Check-out Date', default=fields.Datetime.now, required=True)
    expected_return_date = fields.Date('Expected Return')
    date_to = fields.Datetime('Check-in Date', readonly=True, copy=False)
    condition_out = fields.Selection([
        ('new', 'New'), ('good', 'Good'), ('fair', 'Fair'), ('poor', 'Poor')],
        string='Condition at Check-out', default='good')
    condition_in = fields.Selection([
        ('good', 'Good'), ('fair', 'Fair'), ('poor', 'Poor'), ('damaged', 'Damaged')],
        string='Condition at Check-in')
    note = fields.Text('Notes / Accessories')
    signature = fields.Binary('Employee Signature', copy=False)
    state = fields.Selection([
        ('draft', 'Draft'), ('active', 'Active'),
        ('returned', 'Returned'), ('cancel', 'Cancelled')],
        default='draft', tracking=True, copy=False, required=True)

    is_overdue = fields.Boolean(compute='_compute_is_overdue')

    def _compute_is_overdue(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.is_overdue = bool(rec.state == 'active' and rec.expected_return_date
                                  and rec.expected_return_date < today)

    @api.depends('employee_id')
    def _compute_department(self):
        for rec in self:
            rec.department_id = rec.employee_id.department_id

    @api.constrains('assignment_type', 'expected_return_date')
    def _check_loan(self):
        for rec in self:
            if rec.assignment_type == 'temporary' and not rec.expected_return_date:
                raise ValidationError(self.env._("Temporary loans need an expected return date."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('asset.assignment') or 'New'
        return super().create(vals_list)

    def action_confirm(self):
        """Check-out."""
        for rec in self:
            if rec.state != 'draft':
                continue
            asset = rec.asset_id
            if asset.state != 'available':
                raise UserError(self.env._(
                    "Asset %(asset)s is not available (current status: %(state)s).",
                    asset=asset.display_name, state=dict(asset._fields['state'].selection)[asset.state]))
            asset.write({
                'state': 'in_use',
                'employee_id': rec.employee_id.id,
                'department_id': rec.department_id.id or asset.department_id.id,
                'location_id': rec.location_id.id or asset.location_id.id,
            })
            rec.state = 'active'
            asset.message_post(body=self.env._(
                "Checked out to %s.", rec.employee_id.name))

    def action_return(self):
        """Check-in."""
        for rec in self:
            if rec.state != 'active':
                continue
            asset = rec.asset_id
            rec.write({'state': 'returned', 'date_to': fields.Datetime.now()})
            vals = {'employee_id': False}
            if asset.state == 'in_use':
                vals['state'] = 'available'
            asset.write(vals)
            asset.message_post(body=self.env._("Returned by %s.", rec.employee_id.name))
            if rec.condition_in in ('poor', 'damaged'):
                self.env['asset.maintenance'].create({
                    'asset_id': asset.id,
                    'maintenance_type': 'corrective',
                    'name': self.env._("Inspection after return (%s)", rec.condition_in),
                    'requested_by_id': rec.employee_id.id,
                })

    def action_cancel(self):
        for rec in self:
            if rec.state == 'active':
                raise UserError(self.env._("Return the asset first."))
            rec.state = 'cancel'

    def action_print_handover(self):
        return self.env.ref('asset_management_prime.action_report_asset_handover').report_action(self)
