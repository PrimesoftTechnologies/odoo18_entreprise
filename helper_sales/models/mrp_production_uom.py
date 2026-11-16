# -*- coding: utf-8 -*-

from odoo import api, fields, models


class MrpProductionUom(models.Model):
    _inherit = 'mrp.production'

    # The unit of measure (PCS, Cartons, ...) next to Quantity cannot be changed by the user.
    # It is filled automatically from the Bill of Material / Product as soon as the product is chosen.
    product_uom_id = fields.Many2one(readonly=True)

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == 'form':
            # every occurrence of the field in the form (whatever the view modifiers say)
            for node in arch.xpath("//field[@name='product_uom_id']"):
                node.set('readonly', '1')
                node.set('force_save', '1')
        return arch, view
