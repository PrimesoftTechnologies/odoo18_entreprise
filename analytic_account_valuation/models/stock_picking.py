from odoo import models, fields, Command

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        help="Select analytic account for this delivery order valuation."
    )

    def _prepare_stock_move_vals(self, first_line, order_lines):
        res = super()._prepare_stock_move_vals(first_line, order_lines)
        return res

    def _create_account_move_vals(self, credit_account_id, debit_account_id, journal_id, quant_ids, valued_move_lines, move_id):
        move_vals = super()._create_account_move_vals(credit_account_id, debit_account_id, journal_id, quant_ids, valued_move_lines, move_id)
        if self.analytic_account_id:
            for line in move_vals.get('line_ids', []):
                # line is typically (0, 0, values) or Command.create(values)
                if isinstance(line, (list, tuple)) and len(line) >= 3 and isinstance(line[2], dict):
                    # Add analytic_distribution to line values
                    line[2]['analytic_distribution'] = {str(self.analytic_account_id.id): 100.0}
        return move_vals
