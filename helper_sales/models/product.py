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
            # Kama hakuna default_code na kategoria imechaguliwa
            if not vals.get('default_code') and vals.get('categ_id'):
                category = self.env['product.category'].browse(vals['categ_id'])
                # Inatafuta prefix au short_code kutoka kwenye kategoria au wazazi wake
                prefix_val = False
                curr_cat = category
                while curr_cat and not prefix_val:
                    prefix_val = curr_cat.prefix or curr_cat.short_code
                    curr_cat = curr_cat.parent_id
                
                if prefix_val:
                    # Inatengeneza au kuchukua namba inayofuata ya sequence ya kategoria hiyo
                    seq = self.env['ir.sequence'].next_by_code('product.code.sequence') or '001'
                    vals['default_code'] = f"{prefix_val}{seq}"
            
            # Fallback ya mwisho kama hakuna kategoria yenye prefix
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