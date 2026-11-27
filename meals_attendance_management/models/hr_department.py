from odoo import fields, models


class HrDepartment(models.Model):
    """Departments are owned by a customer (same name allowed for different customers)."""
    _inherit = 'hr.department'

    meal_customer_id = fields.Many2one(
        'res.partner', string='Meals Customer', index=True, ondelete='restrict',
        domain=[('is_meal_customer', '=', True)])

    _sql_constraints = [
        ('meal_customer_name_uniq', 'unique(meal_customer_id, name)',
         'This customer already has a department with the same name.'),
    ]
