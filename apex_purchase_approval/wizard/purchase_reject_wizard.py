from odoo import fields, models


class ApexPurchaseRejectWizard(models.TransientModel):
    _name = 'apex.purchase.reject.wizard'
    _description = 'Purchase Order Rejection'

    order_id = fields.Many2one('purchase.order', required=True, ondelete='cascade')
    reason = fields.Text(string='Reason', required=True)

    def action_reject(self):
        self.ensure_one()
        self.order_id._apex_reject(self.reason)
        return {'type': 'ir.actions.act_window_close'}
