from odoo import models, fields

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        help="Select analytic account for this delivery order valuation."
    )

class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    def _validate_accounting_entries(self):
        res = super()._validate_accounting_entries()
        for layer in self:
            if layer.stock_move_id.picking_id and layer.stock_move_id.picking_id.analytic_account_id:
                analytic_id = layer.stock_move_id.picking_id.analytic_account_id.id
                # Tafuta account moves zinazohusiana na layer hii na uweke analytic distribution
                moves = self.env['account.move'].search([('stock_valuation_layer_ids', 'in', layer.ids)])
                for move in moves:
                    for line in move.line_ids:
                        if not line.analytic_distribution:
                            line.write({
                                'analytic_distribution': {str(analytic_id): 100.0}
                            })
        return res