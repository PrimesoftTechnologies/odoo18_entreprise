from odoo import models, fields, api

class ProductCategory(models.Model):
    _inherit = 'product.category'

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=False,  # Imewekwa False ili isilazimishe mahusiano magumu wakati wa ku-create product
        default=lambda self: self.env.company,
        index=True,
        help="The company related to this category."
    )

