from odoo import api, fields, models


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    control_number = fields.Char(
        string='Control Number',
        compute='_compute_control_number',
        help='Control number(s) of the expense report(s) being paid.',
    )

    @api.depends('line_ids')
    def _compute_control_number(self):
        for wizard in self:
            sheets = wizard.line_ids.move_id.expense_sheet_id
            numbers = list(dict.fromkeys(n for n in sheets.mapped('control_number') if n))
            wizard.control_number = ', '.join(numbers) if numbers else False
