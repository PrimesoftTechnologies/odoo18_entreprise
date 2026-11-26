from odoo import fields, models


class PurchaseOrderApprovalLine(models.Model):
    _name = 'purchase.order.approval.line'
    _description = 'Purchase Order Approval Line'
    _order = 'id'

    order_id = fields.Many2one(
        'purchase.order', required=True, ondelete='cascade', index=True)
    user_id = fields.Many2one('res.users', string='Approver', required=True)
    state = fields.Selection(
        [('pending', 'Pending'),
         ('approved', 'Approved'),
         ('rejected', 'Rejected')],
        default='pending', required=True)
    date = fields.Datetime(string='Date')
    note = fields.Text(string='Comment')
