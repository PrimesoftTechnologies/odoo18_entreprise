from odoo import api, fields, models
from odoo.exceptions import UserError


class AssetTransfer(models.Model):
    _name = 'asset.transfer'
    _description = 'Asset Transfer'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char('Reference', default='New', copy=False, readonly=True)
    asset_id = fields.Many2one('asset.asset', required=True, tracking=True, index=True,
                               domain="[('state', 'in', ('available', 'in_use'))]")
    company_id = fields.Many2one('res.company', required=True,
                                 default=lambda self: self.env.company)
    date = fields.Date(default=fields.Date.context_today, required=True)
    reason = fields.Text()

    from_employee_id = fields.Many2one('hr.employee', compute='_compute_from', store=True,
                                       readonly=False, string='From Employee')
    from_department_id = fields.Many2one('hr.department', compute='_compute_from', store=True,
                                         readonly=False, string='From Department')
    from_location_id = fields.Many2one('asset.location', compute='_compute_from', store=True,
                                       readonly=False, string='From Location')
    to_employee_id = fields.Many2one('hr.employee', string='To Employee', tracking=True)
    to_department_id = fields.Many2one('hr.department', string='To Department', tracking=True)
    to_location_id = fields.Many2one('asset.location', string='To Location', tracking=True)

    approved_by_id = fields.Many2one('res.users', readonly=True, copy=False)
    state = fields.Selection([
        ('draft', 'Draft'), ('submitted', 'Waiting Approval'), ('approved', 'Approved'),
        ('done', 'Done'), ('rejected', 'Rejected'), ('cancel', 'Cancelled')],
        default='draft', tracking=True, copy=False, required=True)

    @api.depends('asset_id')
    def _compute_from(self):
        for rec in self:
            rec.from_employee_id = rec.asset_id.employee_id
            rec.from_department_id = rec.asset_id.department_id
            rec.from_location_id = rec.asset_id.location_id

    @api.onchange('to_employee_id')
    def _onchange_to_employee(self):
        if self.to_employee_id:
            self.to_department_id = self.to_employee_id.department_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('asset.transfer') or 'New'
        return super().create(vals_list)

    def action_submit(self):
        for rec in self:
            if not (rec.to_employee_id or rec.to_department_id or rec.to_location_id):
                raise UserError(self.env._("Choose at least one destination (employee, department or location)."))
            rec.state = 'submitted'

    def action_approve(self):
        self.write({'state': 'approved', 'approved_by_id': self.env.user.id})

    def action_reject(self):
        self.write({'state': 'rejected'})

    def action_cancel(self):
        self.filtered(lambda t: t.state != 'done').write({'state': 'cancel'})

    def action_set_draft(self):
        self.filtered(lambda t: t.state in ('rejected', 'cancel')).write({'state': 'draft'})

    def action_done(self):
        Assignment = self.env['asset.assignment']
        for rec in self:
            if rec.state != 'approved':
                raise UserError(self.env._("The transfer must be approved first."))
            asset = rec.asset_id
            asset.assignment_ids.filtered(lambda a: a.state == 'active').action_return()
            if rec.to_location_id:
                asset.location_id = rec.to_location_id
            if rec.to_department_id:
                asset.department_id = rec.to_department_id
            if rec.to_employee_id:
                assignment = Assignment.create({
                    'asset_id': asset.id,
                    'employee_id': rec.to_employee_id.id,
                    'department_id': rec.to_department_id.id or rec.to_employee_id.department_id.id,
                    'location_id': rec.to_location_id.id or asset.location_id.id,
                    'note': self.env._("Created by transfer %s", rec.name),
                })
                assignment.action_confirm()
            asset.message_post(body=self.env._("Transfer %s completed.", rec.name))
            rec.state = 'done'
