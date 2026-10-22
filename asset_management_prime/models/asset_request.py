from odoo import api, fields, models
from odoo.exceptions import UserError


class AssetRequest(models.Model):
    _name = 'asset.request'
    _description = 'Asset Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char('Reference', default='New', copy=False, readonly=True)
    title = fields.Char('Subject', required=True, tracking=True)
    company_id = fields.Many2one('res.company', required=True,
                                 default=lambda self: self.env.company)
    employee_id = fields.Many2one('hr.employee', string='Requested By', required=True,
                                  default=lambda self: self.env.user.employee_id, tracking=True)
    department_id = fields.Many2one('hr.department', compute='_compute_department',
                                    store=True, readonly=False)
    category_id = fields.Many2one('asset.category', string='Asset Category', required=True)
    quantity = fields.Integer(default=1)
    needed_date = fields.Date('Needed By')
    priority = fields.Selection([('0', 'Normal'), ('1', 'High'), ('2', 'Urgent')], default='0')
    estimated_cost = fields.Monetary(currency_field='currency_id')
    currency_id = fields.Many2one(related='company_id.currency_id')
    justification = fields.Text(required=True)
    state = fields.Selection([
        ('draft', 'Draft'), ('submitted', 'Department Approval'),
        ('dept_approved', 'Asset Manager Approval'), ('approved', 'Approved'),
        ('fulfilled', 'Fulfilled'), ('rejected', 'Rejected'), ('cancel', 'Cancelled')],
        default='draft', tracking=True, copy=False, required=True)
    asset_id = fields.Many2one('asset.asset', string='Created Asset', readonly=True, copy=False)
    reject_reason = fields.Text(readonly=True)

    @api.depends('employee_id')
    def _compute_department(self):
        for rec in self:
            rec.department_id = rec.employee_id.department_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('asset.request') or 'New'
        return super().create(vals_list)

    def _is_dept_manager(self):
        self.ensure_one()
        manager_user = self.department_id.manager_id.user_id
        return (manager_user == self.env.user
                or self.env.user.has_group('asset_management_prime.group_asset_manager'))

    def action_submit(self):
        for rec in self:
            rec.state = 'submitted'
            manager = rec.department_id.manager_id.user_id
            if manager:
                rec.activity_schedule('mail.mail_activity_data_todo',
                                      summary=self.env._("Approve asset request"), user_id=manager.id)

    def action_dept_approve(self):
        for rec in self:
            if not rec._is_dept_manager():
                raise UserError(self.env._("Only the department manager can approve this request."))
            rec.activity_feedback(['mail.mail_activity_data_todo'])
            rec.state = 'dept_approved'

    def action_approve(self):
        if not self.env.user.has_group('asset_management_prime.group_asset_manager'):
            raise UserError(self.env._("Only an Asset Manager can give the final approval."))
        self.write({'state': 'approved'})

    def action_reject(self):
        self.write({'state': 'rejected'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_set_draft(self):
        self.filtered(lambda r: r.state in ('rejected', 'cancel')).write({'state': 'draft'})

    def action_create_asset(self):
        self.ensure_one()
        asset = self.env['asset.asset'].create({
            'name': self.title,
            'category_id': self.category_id.id,
            'department_id': self.department_id.id,
            'purchase_value': self.estimated_cost,
        })
        self.write({'asset_id': asset.id, 'state': 'fulfilled'})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'asset.asset',
            'res_id': asset.id,
            'view_mode': 'form',
        }
