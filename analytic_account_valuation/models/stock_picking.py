from odoo import models, fields

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        help="Select analytic account for this delivery order valuation."
    )
