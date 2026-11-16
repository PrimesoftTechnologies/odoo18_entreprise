# -*- coding: utf-8 -*-

from odoo import fields, models


class MrpProductionUom(models.Model):
    _inherit = 'mrp.production'

    # The unit of measure (PCS, Cartons, ...) next to Quantity cannot be changed by the user.
    # It is still filled automatically from the Bill of Material / Product.
    product_uom_id = fields.Many2one(readonly=True)
