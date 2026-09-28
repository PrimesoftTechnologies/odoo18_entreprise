from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    order_type = fields.Selection([
        ('po', 'Material PO'),
        ('wo', 'Subcontractor Work Order'),
        ('ao', 'Advance / Asset Order')
    ], string='Order Type', default='po', required=True, tracking=True)

    project_id = fields.Many2one('estate.project', string='Real Estate Project', tracking=True)
    retention_percentage = fields.Float(string='Retention Money (%)', default=0.0, tracking=True)
    retention_amount = fields.Monetary(string='Retention Amount', compute='_compute_retention_amount', store=True)

    negotiation_notes = fields.Text(string='Negotiation Notes & Terms')
    approval_limit = fields.Monetary(string='Threshold Approval Limit', default=50000.0)
    requires_manager_approval = fields.Boolean(string='Requires Manager Approval', compute='_compute_manager_approval', store=True)
    manager_approved = fields.Boolean(string='Manager Approved', default=False, tracking=True)

    @api.depends('amount_total', 'retention_percentage')
    def _compute_retention_amount(self):
        for order in self:
            order.retention_amount = order.amount_total * (order.retention_percentage / 100.0)

    @api.depends('amount_total', 'approval_limit')
    def _compute_manager_approval(self):
        for order in self:
            order.requires_manager_approval = order.amount_total > order.approval_limit

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('project_id') and vals.get('order_type'):
                project = self.env['estate.project'].browse(vals['project_id'])
                order_prefix = vals['order_type'].upper()
                year_str = datetime.now().strftime('%Y')
                seq_code = 'estate.purchase.order.custom.seq'
                seq = self.env['ir.sequence'].next_by_code(seq_code) or '0001'
                vals['name'] = f"{order_prefix}/{project.code or 'PROJ'}/{year_str}/{seq}"
        return super().create(vals_list)

    def button_confirm(self):
        for order in self:
            if order.requires_manager_approval and not order.manager_approved:
                if not self.env.user.has_group('ad_estate_base.group_estate_manager'):
                    raise UserError(_("Order amount %s exceeds approval limit %s. This order requires Estate Project Manager approval before confirmation.") % (
                        order.amount_total, order.approval_limit
                    ))
        return super().button_confirm()

    def action_manager_approve(self):
        self.ensure_one()
        self.write({'manager_approved': True})
