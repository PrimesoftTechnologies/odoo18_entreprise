# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError


def _check_update_quantity_access(env):
    if env.su:
        return
    if not env.user.has_group('helper_sales.group_update_quantity'):
        raise UserError(_("You are not allowed to use 'Update Quantity'. Please contact the authorised person."))


class ProductCategory(models.Model):
    _inherit = 'product.category'

    short_code = fields.Char(string='Short Code', help="Mfano: FG, RM, n.k.")
    prefix = fields.Char(string='Prefix', help="Sehemu ya mbele ya namba, mfano: FG au namba maalum")


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Kama hakuna default_code iliyojazwa na kategoria imechaguliwa
            if not vals.get('default_code') and vals.get('categ_id'):
                category = self.env['product.category'].browse(vals['categ_id'])
                prefix_val = category.prefix or category.short_code
                if prefix_val:
                    # Inatumia sequence au inatengeneza namba inayofuata kulingana na prefix
                    seq = self.env['ir.sequence'].next_by_code('product.code.sequence') or '001'
                    vals['default_code'] = f"{prefix_val}{seq}"
            
            # Fallback ya zamani kama hakuna kategoria yenye prefix
            elif not vals.get('default_code') and not self.env.context.get('install_mode'):
                sequence = self.env['ir.sequence']
                vals['default_code'] = sequence.next_by_code('helper_sales.product.reference')

        return super().create(vals_list)

    def copy_data(self, default=None):
        default = dict(default or {})
        default.setdefault('default_code', False)  # a duplicated product gets a new reference
        return super().copy_data(default)

    def action_update_quantity_on_hand(self):
        _check_update_quantity_access(self.env)
        return super().action_update_quantity_on_hand()


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def action_update_quantity_on_hand(self):
        _check_update_quantity_access(self.env)
        return super().action_update_quantity_on_hand()