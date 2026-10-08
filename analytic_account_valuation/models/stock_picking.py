from odoo import models, fields

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    analytic_distribution = fields.Json(
        string='Analytic Distribution',
        help="Analytic distribution for valuation moves."
    )
    analytic_precision = fields.Integer(
        string="Analytic Precision",
        compute="_compute_analytic_precision",
        store=False,
    )

    def _compute_analytic_precision(self):
        for picking in self:
            picking.analytic_precision = self.env['account.move.line']._fields['analytic_distribution'].get_digits(self.env)

class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    def _validate_accounting_entries(self):
        res = super()._validate_accounting_entries()
        for layer in self:
            picking = layer.stock_move_id.picking_id
            if picking and picking.analytic_distribution:
                moves = self.env['account.move'].search([('stock_valuation_layer_ids', 'in', layer.ids)])
                for move in moves:
                    for line in move.line_ids:
                        if not line.analytic_distribution:
                            line.write({
                                'analytic_distribution': picking.analytic_distribution
                            })
        return res