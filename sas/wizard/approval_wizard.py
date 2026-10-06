from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ShippingOrderRejectWizard(models.TransientModel):
    """
    Wizard to capture rejection reason before returning an order to draft.
    Used for both L1 and L2 rejection.
    """
    _name = 'shipping.order.reject.wizard'
    _description = 'Reject Shipping Order'

    shipping_order_id = fields.Many2one('shipping.order', string='Shipping Order', required=True)
    rejection_reason = fields.Text(
        string='Reason for Rejection',
        required=True,
        help="This reason will be sent to the submitter by email.",
    )

    def action_reject(self):
        self.ensure_one()
        order = self.shipping_order_id
        order.write({
            'state': 'draft',
            'rejection_reason': self.rejection_reason,
            'rejection_date': fields.Date.today(),
        })
        order.message_post(
            body=_("Order rejected and returned to draft. Reason: %s") % self.rejection_reason
        )
        # Send rejection email
        template = self.env.ref(
            'sas_logistics.email_template_order_rejected', raise_if_not_found=False
        )
        if template:
            template.send_mail(order.id, force_send=True)
        return {'type': 'ir.actions.act_window_close'}