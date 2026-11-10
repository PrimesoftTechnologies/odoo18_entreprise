# -*- coding: utf-8 -*-

from odoo import models, fields, _
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    def action_generate_product_references(self):
        """Inapitia bidhaa zote ambazo hazina Internal Reference au zinahitaji kusasishwa
           kulingana na Short Code na Prefix ya kategoria zake."""
        products = self.env['product.template'].search([('default_code', '=', False)])
        
        count = 0
        for product in products:
            if product.categ_id:
                short_code = False
                prefix_val = False
                curr_cat = product.categ_id
                while curr_cat and not (short_code or prefix_val):
                    short_code = short_code or curr_cat.short_code
                    prefix_val = prefix_val or curr_cat.prefix
                    curr_cat = curr_cat.parent_id

                seq = self.env['ir.sequence'].next_by_code('product.code.sequence') or '001'
                
                parts = []
                if short_code:
                    parts.append(short_code)
                if prefix_val:
                    parts.append(prefix_val)
                parts.append(seq)

                if parts:
                    product.default_code = "".join(parts)
                    count += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success!'),
                'message': _('Internal Reference codes for %s products have been generated successfully.') % count,
                'sticky': False,
                'type': 'success',
            }
        }