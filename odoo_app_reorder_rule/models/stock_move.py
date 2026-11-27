import logging

from odoo import models

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = "stock.move"

    def _action_done(self, cancel_backorder=False):
        moves = super()._action_done(cancel_backorder=cancel_backorder)
        try:
            with self.env.cr.savepoint():
                products = (moves | self).product_id
                self.env["reorder.alert"]._check_products(products)
        except Exception:
            _logger.exception("Reorder alert check after stock move failed")
        return moves
