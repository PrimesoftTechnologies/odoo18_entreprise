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
    prefix = fields.Char(string='Prefix', help="Sehemu ya namba au ziada, mfano: 5")
    auto_generate_ref = fields.Boolean(
        string='Auto Generate Reference', 
        default=True,
        help="Washa (On) ili kuruhusu bidhaa za kategoria hii kupata Internal Reference kiotomatiki."
    )


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('default_code'):
                short_code = False
                prefix_val = False
                auto_gen = False
                
                if vals.get('categ_id'):
                    category = self.env['product.category'].browse(vals['categ_id'])
                    curr_cat = category
                    while curr_cat and not (short_code or prefix_val):
                        short_code = short_code or curr_cat.short_code
                        prefix_val = prefix_val or curr_cat.prefix
                        auto_gen = curr_cat.auto_generate_ref
                        # Kama kategoria ya juu imezimwa, tunaiweka false
                        if not curr_cat.auto_generate_ref:
                            auto_gen = False
                            break
                        curr_cat = curr_cat.parent_id

                # Inatengeneza code tu kama auto_generate_ref ipo 'True' (On)
                if auto_gen and (short_code or prefix_val):
                    seq = self.env['ir.sequence'].next_by_code('product.code.sequence') or '001'
                    parts = []
                    if short_code:
                        parts.append(short_code)
                    if prefix_val:
                        parts.append(prefix_val)
                    parts.append(seq)
                    vals['default_code'] = "".join(parts)
                else:
                    # Kama imezimwa (Off), hakuna reference itakayozalishwa (inabaki tupu)
                    vals['default_code'] = False

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