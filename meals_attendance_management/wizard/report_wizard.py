from odoo import _, fields, models
from odoo.exceptions import UserError


class MealsReportWizard(models.TransientModel):
    _name = 'meals.report.wizard'
    _description = 'Customer Meals Statement Wizard'

    customer_id = fields.Many2one('res.partner', string='Customer', required=True,
                                  domain=[('is_meal_customer', '=', True)])
    date_from = fields.Date(required=True, default=lambda s: fields.Date.today().replace(day=1))
    date_to = fields.Date(required=True, default=fields.Date.context_today)
    meal_type_ids = fields.Many2many(
        'meals.type', string='Meal Types', domain="[('customer_id', '=', customer_id)]",
        help="Leave empty for all meal types.")

    def action_print(self):
        self.ensure_one()
        if self.date_from > self.date_to:
            raise UserError(_("'Date From' must be before 'Date To'."))
        data = {
            'customer_id': self.customer_id.id,
            'date_from': fields.Date.to_string(self.date_from),
            'date_to': fields.Date.to_string(self.date_to),
            'meal_type_ids': self.meal_type_ids.ids,
        }
        return self.env.ref(
            'meals_attendance_management.action_report_customer_statement'
        ).report_action(self, data=data)
