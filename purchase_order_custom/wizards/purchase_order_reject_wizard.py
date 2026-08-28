from odoo import api, fields, models

class PurchaseOrderRejectWizard(models.TransientModel):
    _name = 'purchase.order.reject.wizard'
    _description = 'Purchase Order Reject Reason Wizard'

    order_id = fields.Many2one('purchase.order', string="Purchase Order", required=True)
    reject_reason = fields.Text(string="Reason for Rejection", required=True)

    def action_confirm_reject(self):
        self.ensure_one()
        self.order_id.write({
            'reject_reason': self.reject_reason,
            'state': 'rejected',           # Badilisha iwe 'rejected' ili iendane na state mpya ya mfumo
            'approval_stage': 'rejected',  # Stage inakuwa rejected rasmi
        })
        self.order_id.modified(['state', 'approval_stage', 'approval_statusbar', 'reject_reason'])
        return {'type': 'ir.actions.act_window_close'}