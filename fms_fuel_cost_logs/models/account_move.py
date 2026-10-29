from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    fuel_cost_id = fields.Many2one('fms.fuel.cost', string='Fuel Cost', copy=False, readonly=True)
