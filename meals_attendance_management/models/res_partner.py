from odoo import api, fields, models


class ResPartner(models.Model):
    """Customer = res.partner flagged as Meals Customer (inherit, nothing new)."""
    _inherit = 'res.partner'

    is_meal_customer = fields.Boolean(
        string='Meals Customer',
        help="Tick to use this partner as a customer of the Meals Attendance module.")
    meal_employee_count = fields.Integer(compute='_compute_meal_counts')
    meal_type_count = fields.Integer(compute='_compute_meal_counts')
    meal_attendance_count = fields.Integer(compute='_compute_meal_counts')

    @api.depends('is_meal_customer')
    def _compute_meal_counts(self):
        Employee = self.env['hr.employee'].sudo()
        MealType = self.env['meals.type'].sudo()
        Attendance = self.env['meals.attendance'].sudo()
        for partner in self:
            pid = partner._origin.id
            if partner.is_meal_customer and pid:
                partner.meal_employee_count = Employee.search_count([('meal_customer_id', '=', pid)])
                partner.meal_type_count = MealType.search_count([('customer_id', '=', pid)])
                partner.meal_attendance_count = Attendance.search_count([('customer_id', '=', pid)])
            else:
                partner.meal_employee_count = 0
                partner.meal_type_count = 0
                partner.meal_attendance_count = 0

    def _meals_action(self, xmlid, domain, context):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(xmlid)
        action['domain'] = domain
        action['context'] = context
        return action

    def action_view_meal_employees(self):
        return self._meals_action(
            'meals_attendance_management.action_meals_employee',
            [('meal_customer_id', '=', self.id)],
            {'default_meal_customer_id': self.id, 'default_is_meal_employee': True})

    def action_view_meal_types(self):
        return self._meals_action(
            'meals_attendance_management.action_meals_type',
            [('customer_id', '=', self.id)],
            {'default_customer_id': self.id})

    def action_view_meal_attendances(self):
        return self._meals_action(
            'meals_attendance_management.action_meals_attendance',
            [('customer_id', '=', self.id)],
            {'default_customer_id': self.id})
