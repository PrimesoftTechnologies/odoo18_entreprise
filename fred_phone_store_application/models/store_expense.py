from odoo import fields, models


class FredStoreExpense(models.Model):
    _name = 'fred.store.expense'
    _description = 'Phone Store Expense'
    _order = 'date desc, id desc'

    name = fields.Char(string='Description', required=True)
    date = fields.Date(required=True, default=fields.Date.context_today)
    expense_type_id = fields.Many2one(
        'fred.expense.type', string='Expense Type', required=True,
        ondelete='restrict')
    amount = fields.Monetary(required=True)
    config_id = fields.Many2one(
        'pos.config', string='Shop',
        help='Leave empty for general expenses that apply to all shops.')
    note = fields.Text()
    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id', store=True)
