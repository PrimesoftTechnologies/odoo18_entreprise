from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_not_commission = fields.Boolean(
        string="Not Commission Product",
        default=False,
        help="Check this box if this product should be excluded from employee commission calculations."
    )