from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class HrExpenseSheet(models.Model):
    _inherit = 'hr.expense.sheet'

    control_number = fields.Char(
        string='Control Number',
        compute='_compute_control_number',
        store=True,
        readonly=False,
        precompute=True,
        tracking=True,
        help='Control number carried over from the expenses of this report. '
             'It is locked once the report leaves the Draft state.',
    )

    @api.depends('expense_line_ids.control_number')
    def _compute_control_number(self):
        for sheet in self:
            numbers = list(dict.fromkeys(n for n in sheet.expense_line_ids.mapped('control_number') if n))
            if numbers:
                sheet.control_number = numbers[0]
            elif not sheet.control_number:
                sheet.control_number = False

    @api.constrains('expense_line_ids')
    def _check_control_number_consistency(self):
        for sheet in self:
            numbers = set(n for n in sheet.expense_line_ids.mapped('control_number') if n)
            if len(numbers) > 1:
                raise ValidationError(_(
                    "The expenses in report %(sheet)s have different Control Numbers (%(numbers)s). "
                    "Give them the same Control Number, or split them into separate reports.",
                    sheet=sheet.name or sheet.display_name,
                    numbers=', '.join(sorted(numbers)),
                ))
