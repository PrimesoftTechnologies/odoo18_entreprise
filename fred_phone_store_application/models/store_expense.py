from odoo import fields, models

EXPENSE_CATEGORIES = [
    ('rent', 'Rent'),
    ('salary', 'Salaries'),
    ('electricity', 'Electricity / Water'),
    ('transport', 'Transport'),
    ('marketing', 'Marketing / Advertising'),
    ('repair', 'Repairs / Maintenance'),
    ('tax', 'Taxes / Licenses'),
    ('other', 'Other'),
]


class FredStoreExpense(models.Model):
    _name = 'fred.store.expense'
    _description = 'Phone Store Expense'
    _order = 'date desc, id desc'

    name = fields.Char(string='Description', required=True)
    date = fields.Date(required=True, default=fields.Date.context_today)
    category = fields.Selection(EXPENSE_CATEGORIES, required=True, default='other')
    amount = fields.Monetary(required=True)
    config_id = fields.Many2one(
        'pos.config', string='Shop',
        help='Leave empty for general expenses that apply to all shops.')
    note = fields.Text()
    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id', store=True)
