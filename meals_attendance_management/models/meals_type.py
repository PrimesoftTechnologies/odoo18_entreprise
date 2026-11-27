from odoo import fields, models


class MealsType(models.Model):
    _name = 'meals.type'
    _description = 'Meal Type (per customer)'
    _order = 'customer_id, sequence, start_time, id'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    customer_id = fields.Many2one(
        'res.partner', string='Customer', required=True, index=True, ondelete='restrict',
        domain=[('is_meal_customer', '=', True)])
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company, required=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    price = fields.Monetary(string='Price per Meal', currency_field='currency_id', required=True)
    start_time = fields.Float(string='From')
    end_time = fields.Float(string='To')

    _sql_constraints = [
        ('customer_name_uniq', 'unique(customer_id, name)',
         'This customer already has a meal type with the same name.'),
    ]
