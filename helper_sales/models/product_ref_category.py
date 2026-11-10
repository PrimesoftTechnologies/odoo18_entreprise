# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ProductRefCategory(models.Model):
    _name = 'product.ref.category'
    _description = 'Product Reference Category'

    name = fields.Char(string='Category Name', required=True)
    prefix = fields.Char(string='Prefix / Code', required=True, help="Mfano: PM, au namba kama 1, 2")


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    ref_category_id = fields.Many2one(
        'product.ref.category', 
        string='Reference Category',
        help="Chagua kategoria ili kujaza namba ya Internal Reference kiotomatiki kulingana na prefix."
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('ref_category_id') and not vals.get('default_code'):
                category = self.env['product.ref.category'].browse(vals['ref_category_id'])
                if category and category.prefix:
                    # Inatafuta namba inayofuata au kutumia sequence ya kipekee
                    seq = self.env['ir.sequence'].next_by_code('product.ref.category.sequence') or '0001'
                    vals['default_code'] = f"{category.prefix}{seq}"
        return super().create(vals_list)