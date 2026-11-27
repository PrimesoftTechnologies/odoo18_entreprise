# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


def _check_update_quantity_access(env):
    if env.su:
        return
    if not env.user.has_group('helper_sales.group_update_quantity'):
        raise UserError(_("You are not allowed to use 'Update Quantity'. Please contact the authorised person."))


class ProductCategory(models.Model):
    _inherit = 'product.category'

    short_code = fields.Char(
        string='Prefix',
        help="Mfano: RM kwa Raw Material, CM kwa Consumable Material."
    )
    prefix = fields.Char(
        string='Sequence Number',
        default='5',
        help="Weka idadi ya tarakimu (mfano 5 -> 00001, 6 -> 000001)."
    )
    auto_generate_ref = fields.Boolean(
        string='Auto Generate Reference',
        default=True,
        help="Washa (On) ili kuruhusu bidhaa za kategoria hii kupata Internal Reference kiotomatiki."
    )
    last_sequence = fields.Integer(
        string='Last Sequence',
        default=0,
        copy=False,
        help="Namba ya mwisho iliyotumika kwa kategoria hii."
    )

    @api.constrains('prefix', 'auto_generate_ref')
    def _check_prefix_digits(self):
        for rec in self:
            if rec.auto_generate_ref and rec.prefix:
                val = rec.prefix.strip()
                if not val.isdigit() or int(val) < 1:
                    raise ValidationError(_(
                        "Sequence Number kwenye kategoria '%s' lazima iwe namba chanya ya tarakimu (mfano 4, 5, au 6)."
                    ) % rec.display_name)

    def _get_padding_length(self):
        self.ensure_one()
        if self.prefix and self.prefix.strip().isdigit():
            return max(1, int(self.prefix.strip()))
        return 5

    def _get_effective_ref_config(self):
        """Hurejesha (auto_gen, short_code, padding, source_category) kwa kategoria hii au mzazi wake."""
        self.ensure_one()
        curr = self
        short_code = False
        padding = False
        source_cat = False

        while curr:
            if not curr.auto_generate_ref:
                return False, False, False, False
            if curr.short_code and not short_code:
                short_code = curr.short_code.strip().upper()
            if curr.prefix and curr.prefix.strip().isdigit() and not padding:
                padding = int(curr.prefix.strip())
            if curr.short_code and not source_cat:
                source_cat = curr
            curr = curr.parent_id

        if not short_code:
            return False, False, False, False

        return True, short_code, padding or 5, source_cat or self

    def generate_next_product_reference(self):
        """Hupandisha sequence ya kategoria kwa atomic UPDATE ... RETURNING na kurejesha code kama RM00001."""
        self.ensure_one()
        auto_gen, code_prefix, padding, target_cat = self._get_effective_ref_config()
        if not auto_gen or not code_prefix:
            return False

        self.env.cr.execute(
            """
            UPDATE product_category
               SET last_sequence = COALESCE(last_sequence, 0) + 1
             WHERE id = %s
         RETURNING last_sequence
            """,
            [target_cat.id],
        )
        row = self.env.cr.fetchone()
        current_seq = row[0] if row and row[0] else 1
        target_cat.invalidate_recordset(['last_sequence'])

        number_part = str(current_seq).zfill(padding)
        return f"{code_prefix}{number_part}"


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('default_code') and vals.get('categ_id'):
                category = self.env['product.category'].browse(vals['categ_id'])
                generated_ref = category.generate_next_product_reference()
                if generated_ref:
                    vals['default_code'] = generated_ref
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