# -*- coding: utf-8 -*-
"""Hide the 'Update Quantity' button on the Product form for everybody who is not in the
'Helper Sales: Can Update Quantity' group. (The server-side lock in product.py stays as it is.)"""

from odoo import api, models

UPDATE_QTY_GROUP = 'helper_sales.group_update_quantity'


def _restrict_update_quantity_button(arch):
    for node in arch.xpath("//button[@name='action_update_quantity_on_hand']"):
        node.set('groups', UPDATE_QTY_GROUP)


class ProductTemplateHideUpdateQty(models.Model):
    _inherit = 'product.template'

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == 'form':
            _restrict_update_quantity_button(arch)
        return arch, view


class ProductProductHideUpdateQty(models.Model):
    _inherit = 'product.product'

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == 'form':
            _restrict_update_quantity_button(arch)
        return arch, view
