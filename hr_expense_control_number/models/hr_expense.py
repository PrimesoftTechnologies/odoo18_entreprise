from odoo import fields, models


class HrExpense(models.Model):
    _inherit = 'hr.expense'

    control_number = fields.Char(
        string='Control Number',
        tracking=True,
        help='Optional reference number used to track this expense.',
    )
