from odoo import fields, models


class HrContract(models.Model):
    _inherit = 'hr.contract'

    meals_amount = fields.Monetary(
        string='Meals Amount',
        currency_field='currency_id',
        tracking=True,
        help='Meals amount of the employee, shown next to the Wage on the contract.')
