from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_not_commission = fields.Boolean(
        string="Not Commission Product",
        default=False,
        help="Check this box if this product should be excluded from employee commission calculations."
    )

    is_fixed_commission = fields.Boolean(
        string="Fixed Commission Product",
        default=False,
        help="Check this box if this product has a fixed commission amount."
    )

    fixed_commission_amount = fields.Monetary(
        string="Fixed Commission Amount",
        currency_field="currency_id",
        help="Enter the fixed commission amount for this product."
    )

    @api.constrains('is_not_commission', 'is_fixed_commission', 'fixed_commission_amount')
    def _check_commission_settings(self):
        for record in self:
            # 1. Prevent selecting both options at the same time
            if record.is_not_commission and record.is_fixed_commission:
                raise ValidationError("A product cannot be both 'Not Commission' and 'Fixed Commission' at the same time! Please choose only one.")
            
            # 2. If Fixed Commission is selected, the amount must exist and be greater than 0
            if record.is_fixed_commission and (not record.fixed_commission_amount or record.fixed_commission_amount <= 0):
                raise ValidationError("Please enter a valid Fixed Commission Amount.")