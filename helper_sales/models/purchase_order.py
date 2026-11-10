from odoo import models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def button_confirm(self):
        for order in self:
            order.partner_id.commercial_partner_id._check_tin_required()
        return super().button_confirm()
