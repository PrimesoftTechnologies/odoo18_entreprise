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

    short_code = fields.Char(string='Short Code', help="Mfano: TC, FG, RM, n.k.")
    prefix = fields.Char(string='Prefix', help="Sehemu ya mbele ya namba, mfano: TC")


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Tunapata sequence namba ya kawaida kwanza
            sequence_code = False
            if not self.env.context.get('install_mode'):
                sequence_code = self.env['ir.sequence'].next_by_code('helper_sales.product.reference') or ''

            # Kama kategoria imechaguliwa, tunatafuta short_code au prefix yake
            if vals.get('categ_id'):
                category = self.env['product.category'].browse(vals['categ_id'])
                prefix_val = False
                curr_cat = category
                while curr_cat and not prefix_val:
                    prefix_val = curr_cat.prefix or curr_cat.short_code
                    curr_cat = curr_cat.parent_id
                
                if prefix_val:
                    # Tunaiunganisha prefix na namba ya sequence (Mfano: TC + 8001 = TC8001)
                    vals['default_code'] = f"{prefix_val}{sequence_code}"
                else:
                    vals['default_code'] = sequence_code
            elif not vals.get('default_code'):
                vals['default_code'] = sequence_code

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