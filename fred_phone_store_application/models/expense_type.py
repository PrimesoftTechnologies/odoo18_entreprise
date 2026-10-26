from odoo import fields, models


class FredExpenseType(models.Model):
    _name = 'fred.expense.type'
    _description = 'Phone Store Expense Type'
    _order = 'sequence, name'

    name = fields.Char(string='Expense Type', required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    note = fields.Text(string='Description')

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'This expense type already exists!'),
    ]
