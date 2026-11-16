from odoo import models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _action_done(self):
        res = super()._action_done()
        for picking in self.filtered(lambda p: p.state == 'done'):
            orders = picking.move_ids.purchase_line_id.order_id
            orders.filtered(lambda o: o.apex_level == 'in_transit').write(
                {'apex_level': 'received'}
            )
        return res
