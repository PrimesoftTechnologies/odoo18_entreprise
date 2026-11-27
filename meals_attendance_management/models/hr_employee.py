from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class HrEmployee(models.Model):
    """Customer employees are hr.employee records flagged is_meal_employee."""
    _inherit = 'hr.employee'

    is_meal_employee = fields.Boolean(string='Customer Employee (Meals)', index=True)
    meal_customer_id = fields.Many2one(
        'res.partner', string='Meals Customer', index=True, ondelete='restrict',
        domain=[('is_meal_customer', '=', True)])
    meal_employee_no = fields.Char(string='Employee No.', index=True)

    _sql_constraints = [
        ('meal_customer_employee_no_uniq', 'unique(meal_customer_id, meal_employee_no)',
         'Employee No. must be unique per customer.'),
    ]

    @api.constrains('meal_customer_id', 'department_id')
    def _check_meal_department(self):
        for emp in self:
            dept = emp.department_id
            if emp.meal_customer_id and dept and dept.meal_customer_id != emp.meal_customer_id:
                raise ValidationError(_(
                    "Department '%(dept)s' does not belong to customer '%(cust)s'.",
                    dept=dept.name, cust=emp.meal_customer_id.name))

    @api.onchange('meal_customer_id')
    def _onchange_meal_customer_id(self):
        if self.department_id and self.department_id.meal_customer_id != self.meal_customer_id:
            self.department_id = False
