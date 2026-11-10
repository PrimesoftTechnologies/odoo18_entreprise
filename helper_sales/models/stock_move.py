from odoo import fields, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    # Defined directly (no analytic.mixin) to avoid duplicating stock.move's own fields
    analytic_distribution = fields.Json(string='Analytic Distribution', copy=True)
    analytic_precision = fields.Integer(
        store=False,
        default=lambda self: self.env['decimal.precision'].precision_get('Percentage Analytic'),
    )
