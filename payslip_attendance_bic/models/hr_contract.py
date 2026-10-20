from odoo import api, fields, models

SCHEDULE_PAY_LABELS = {
    'annually': '/ year',
    'semi-annually': '/ half year',
    'quarterly': '/ quarter',
    'bi-monthly': '/ 2 months',
    'monthly': '/ month',
    'semi-monthly': '/ half month',
    'bi-weekly': '/ 2 weeks',
    'weekly': '/ week',
    'daily': '/ day',
}


class HrContract(models.Model):
    _inherit = 'hr.contract'

    meals_amount = fields.Monetary(
        string='Meals Amount',
        currency_field='currency_id',
        tracking=True,
        help='Meals amount of the employee for each Schedule Pay period. '
             'It is prorated on the payslip using the attendance days.')
    meals_period_label = fields.Char(
        string='Meals Period', compute='_compute_meals_period_label')

    @api.depends('schedule_pay')
    def _compute_meals_period_label(self):
        for contract in self:
            contract.meals_period_label = SCHEDULE_PAY_LABELS.get(
                contract.schedule_pay, '/ month')
