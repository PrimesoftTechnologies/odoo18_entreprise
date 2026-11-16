from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    pos_discount_limit = fields.Float(
        string='Limit Sales Price',
        digits='Product Price',
        help="Lowest price this product may be sold for in the Point of Sale. "
             "Example: Sales Price 80,000 and Limit Discount 75,000: the cashier can sell "
             "at 75,000 or more, but not below. Leave 0 for no limit.",
    )

    @api.constrains('pos_discount_limit', 'list_price')
    def _check_pos_discount_limit(self):
        for product in self:
            if product.pos_discount_limit < 0:
                raise ValidationError(_("Limit Discount can not be negative."))
            if product.pos_discount_limit > product.list_price:
                raise ValidationError(_(
                    "Limit Discount (%(limit)s) can not be higher than the Sales Price (%(price)s) "
                    "for product '%(name)s'.",
                    limit=product.pos_discount_limit,
                    price=product.list_price,
                    name=product.display_name,
                ))
