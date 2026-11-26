from odoo import _, api, models
from odoo.exceptions import UserError

LOCKED_LINE_FIELDS = {
    'product_id', 'product_qty', 'price_unit', 'taxes_id', 'name', 'product_uom',
    'date_planned', 'sequence', 'display_type', 'discount', 'product_packaging_id',
    'product_packaging_qty', 'analytic_distribution',
}


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def _oscon_check_locked(self, orders):
        if self.env.su or self.env.context.get('oscon_bypass_lock'):
            return
        for order in orders:
            if order._oscon_is_locked():
                raise UserError(_(
                    'Order %s is locked because it was submitted for approval. '
                    'Use "Set to Draft" first if you need to change it.', order.name))

    @api.model_create_multi
    def create(self, vals_list):
        orders = self.env['purchase.order'].browse(
            [v['order_id'] for v in vals_list if v.get('order_id')])
        self._oscon_check_locked(orders)
        return super().create(vals_list)

    def write(self, vals):
        if LOCKED_LINE_FIELDS & set(vals):
            self._oscon_check_locked(self.order_id)
        return super().write(vals)

    def unlink(self):
        self._oscon_check_locked(self.order_id)
        return super().unlink()
