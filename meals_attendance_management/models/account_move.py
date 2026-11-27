from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    meals_line_ids = fields.One2many('meals.attendance.line', 'invoice_id', string='Meals Attendance Lines')

    def button_cancel(self):
        res = super().button_cancel()
        # release attendance so it can be invoiced again
        self.env['meals.attendance.line'].sudo().search(
            [('invoice_id', 'in', self.ids)]).write({'invoice_id': False})
        return res
