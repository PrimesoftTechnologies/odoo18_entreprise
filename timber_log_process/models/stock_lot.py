from odoo import api, fields, models


class StockLot(models.Model):
    """Each timber log is a standard Odoo Lot. We only add the measurements."""
    _inherit = "stock.lot"

    timber_type = fields.Selection(related="product_id.timber_type", string="Timber Role")
    timber_circumference = fields.Float(string="Circumference (cm)", digits=(16, 2))
    timber_log_length = fields.Float(string="Length (cm)", digits=(16, 2))
    timber_cbm = fields.Float(
        string="Log CBM", compute="_compute_timber_cbm", store=True, digits=(16, 6))

    @api.depends("timber_circumference", "timber_log_length")
    def _compute_timber_cbm(self):
        for lot in self:
            lot.timber_cbm = (
                (lot.timber_circumference ** 2) * lot.timber_log_length / 12566370.0
                if lot.timber_circumference and lot.timber_log_length else 0.0
            )
