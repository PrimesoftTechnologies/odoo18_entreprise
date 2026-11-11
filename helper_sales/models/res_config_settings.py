# -*- coding: utf-8 -*-

from odoo import api, models, fields, _
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    payment_pending_days = fields.Integer(
        string='Days allowed for an unfinished payment',
        config_parameter='helper_sales.payment_pending_days',
        default=1,
        help="A customer with a Draft / In Process payment older than this number of days "
             "cannot get a new payment until the old one is completed.",
    )

    @api.model
    def _get_payment_pending_days(self):
        value = self.env['ir.config_parameter'].sudo().get_param('helper_sales.payment_pending_days', '1')
        try:
            return max(int(value), 0)
        except (TypeError, ValueError):
            return 1

    def action_generate_product_references(self):
        """Inapitia bidhaa zote ambazo hazina Internal Reference na kategoria zake zimewezeshwa Auto Generate."""
        products = self.env['product.template'].search([('default_code', '=', False)])
        
        count = 0
        for product in products:
            if product.categ_id:
                short_code = False
                prefix_val = False
                auto_gen = True
                curr_cat = product.categ_id
                
                while curr_cat and not (short_code or prefix_val):
                    short_code = short_code or curr_cat.short_code
                    prefix_val = prefix_val or curr_cat.prefix
                    if not curr_cat.auto_generate_ref:
                        auto_gen = False
                        break
                    curr_cat = curr_cat.parent_id

                if auto_gen and (short_code or prefix_val):
                    seq = self.env['ir.sequence'].next_by_code('product.code.sequence') or '001'
                    parts = []
                    if short_code:
                        parts.append(short_code)
                    if prefix_val:
                        parts.append(prefix_val)
                    parts.append(seq)

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