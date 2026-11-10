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

    short_code = fields.Char(string='Short Code', help="Mfano: DC, FG, RM, n.k.")
    prefix = fields.Char(string='Prefix', help="Sehemu ya mbele ya namba")


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('default_code'):
                prefix_val = False
                if vals.get('categ_id'):
                    category = self.env['product.category'].browse(vals['categ_id'])
                    curr_cat = category
                    while curr_cat and not prefix_val:
                        # Tunatanguliza short_code, kama haipo tunachukua prefix
                        prefix_val = curr_cat.short_code or curr_cat.prefix
                        curr_cat = curr_cat.parent_id

                if prefix_val:
                    # Inatengeneza au kuchukua namba inayofuata ya sequence kwa ajili ya kategoria hii
                    seq = self.env['ir.sequence'].next_by_code('product.code.sequence') or '001'
                    vals['default_code'] = f"{prefix_val}{seq}"
                else:
                    # Fallback kama hakuna kategoria yenye short_code/prefix
                    vals['default_code'] = self.env['ir.sequence'].next_by_code('helper_sales.product.reference') or ''

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