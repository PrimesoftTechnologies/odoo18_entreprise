from odoo import models, fields

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        help="Select analytic account for this delivery order valuation."
    )

    def _create_account_move(self, credit_account_id, debit_account_id, journal_id, quant_ids, valued_move_lines):
        move = super()._create_account_move(credit_account_id, debit_account_id, journal_id, quant_ids, valued_move_lines)
        if self.analytic_account_id and move:
            for line in move.line_ids:
                # Apply analytic distribution to lines that don't have it or all lines
                line.write({
                    'analytic_distribution': {str(self.analytic_account_id.id): 100.0}
                })
        return move
