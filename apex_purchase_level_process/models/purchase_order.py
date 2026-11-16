from odoo import api, models, fields, _
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    apex_level = fields.Selection(
        [
            ('collected', 'Collected Order'),
            ('in_transit', 'In-Transit'),
            ('received', 'Received'),
        ],
        string='Process Level',
        copy=False,
        tracking=True,
    )

    # Single combined status for the header: RFQ -> RFQ Sent -> Purchase Order
    # -> Collected Order -> In-Transit -> Received
    apex_status = fields.Selection(
        [
            ('draft', 'RFQ'),
            ('sent', 'RFQ Sent'),
            ('to approve', 'To Approve'),
            ('purchase', 'Purchase Order'),
            ('collected', 'Collected Order'),
            ('in_transit', 'In-Transit'),
            ('received', 'Received'),
            ('done', 'Locked'),
            ('cancel', 'Cancelled'),
        ],
        string='Status',
        compute='_compute_apex_status',
        store=True,
    )

    @api.depends('state', 'apex_level')
    def _compute_apex_status(self):
        for order in self:
            if order.state in ('purchase', 'done') and order.apex_level:
                order.apex_status = order.apex_level
            else:
                order.apex_status = order.state

    def action_apex_collected(self):
        for order in self:
            if order.state != 'purchase':
                raise UserError(_("The order must be confirmed first."))
            order.apex_level = 'collected'

    def action_apex_in_transit(self):
        for order in self:
            if order.apex_level != 'collected':
                raise UserError(_("The order must be Collected first."))
            order.apex_level = 'in_transit'
