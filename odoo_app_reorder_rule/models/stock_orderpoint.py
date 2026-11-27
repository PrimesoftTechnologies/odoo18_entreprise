import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class StockWarehouseOrderpoint(models.Model):
    _inherit = "stock.warehouse.orderpoint"

    def _reorder_alert_check(self):
        try:
            with self.env.cr.savepoint():
                self.env["reorder.alert"]._check_orderpoints(self)
        except Exception:
            _logger.exception("Reorder alert check failed")

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._reorder_alert_check()
        return records

    def write(self, vals):
        res = super().write(vals)
        if {"product_min_qty", "product_id", "location_id", "active"} & set(vals):
            self._reorder_alert_check()
        return res
