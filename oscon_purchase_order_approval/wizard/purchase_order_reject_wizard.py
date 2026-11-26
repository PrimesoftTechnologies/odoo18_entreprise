from odoo import fields, models


class PurchaseOrderRejectWizard(models.TransientModel):
    _name = 'purchase.order.reject.wizard'
    _description = 'Purchase Order Rejection Wizard'

    order_id = fields.Many2one('purchase.order', required=True)
    reason = fields.Text(string='Reason', required=True)

    def action_confirm_reject(self):
        self.ensure_one()
        self.order_id._do_reject(self.reason)
        return {'type': 'ir.actions.act_window_close'}
