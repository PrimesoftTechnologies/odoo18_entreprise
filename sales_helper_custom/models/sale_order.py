from odoo import models, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    helper_id = fields.Many2one(
        'res.users', 
        string='Helper', 
        tracking=True
    )
