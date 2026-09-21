from odoo import models, fields

class TimberExpense(models.Model):
    _name = 'timber.expense'
    _description = 'Timber Expense'

    name = fields.Char(string='Expense Ref', required=True)
    # Ongeza uwanja huu ili uweze kuunganisha expense na gogo husika
    timber_log_id = fields.Many2one('timber.log', string='Timber Log', ondelete='cascade')
    
    amount = fields.Monetary(string='Amount', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('cancel', 'Cancelled')
    ], string='Status', default='draft')
    date = fields.Date(string='Date', default=fields.Date.today)