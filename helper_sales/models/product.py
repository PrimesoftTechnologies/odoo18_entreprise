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

    short_code = fields.Char(string='Short Code', help="Mfano: HDC, FG, RM, n.k.")
    prefix = fields.Char(string='Prefix', help="Sehemu ya namba au ziada, mfano: 5")


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('default_code'):
                short_code = False
                prefix_val = False
                if vals.get('categ_id'):
                    category = self.env['product.category'].browse(vals['categ_id'])
                    curr_cat = category
                    while curr_cat and not (short_code or prefix_val):
                        short_code = short_code or curr_cat.short_code
                        prefix_val = prefix_val or curr_cat.prefix
                        curr_cat = curr_cat.parent_id

                # Tunapata namba ya sequence (mfano 001)
                seq = self.env['ir.sequence'].next_by_code('product.code.sequence') or '001'

                # Tunatengeneza muundo: Short Code + Prefix + Sequence (Au unaweza kubadilisha ikawa unavyotaka)
                parts = []
                if short_code:
                    parts.append(short_code)
                if prefix_val:
                    parts.append(prefix_val)
                parts.append(seq)

                if parts:
                    vals['default_code'] = "".join(parts) # Mfano: HDC + 5 + 001 = HDC5001 (au kama unataka iwe na separator weka '-')
                else:
                    vals['default_code'] = self.env['ir.sequence'].next_by_code('helper_sales.product.reference') or ''

        return super().create(vals_list)

    def copy_data(self, default=None):
        default = dict(default or {})
        default.setdefault('default_code', False)
        return super().copy_data(default)

    def action_update_quantity_on_hand(self):
        _check_update_quantity_access(self.env)
        return super().action_update_quantity_on_hand()


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def action_update_quantity_on_hand(self):
        _check_update_quantity_access(self.env)
        return super().action_update_quantity_on_hand()