# -*- coding: utf-8 -*-

from datetime import timedelta
from odoo import api, models, fields, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    account_reviewer_ids = fields.Many2many(
        'res.users', 'company_account_reviewer_rel',
        'company_id', 'user_id', string="Account Reviewers"
    )


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    payment_pending_days = fields.Integer(
        string='Time allowed for an unfinished payment',
        config_parameter='helper_sales.payment_pending_days',  # same key as before, so the saved value is kept
        default=1,
        help="A customer with a Draft / In Process payment older than this time "
             "cannot get a new payment until the old one is completed.",
    )
    payment_pending_unit = fields.Selection(
        [('minutes', 'Minutes'), ('hours', 'Hours'), ('days', 'Days'), ('weeks', 'Weeks')],
        string='Time unit',
        config_parameter='helper_sales.payment_pending_unit',
        default='days',
    )
    account_reviewer_ids = fields.Many2many(
        'res.users', related='company_id.account_reviewer_ids',
        readonly=False, string="Account Reviewers"
    )

    @api.model
    def _get_payment_pending_limit(self):
        """ Returns (timedelta, readable label) for the unfinished-payment rule. """
        params = self.env['ir.config_parameter'].sudo()
        try:
            value = max(int(params.get_param('helper_sales.payment_pending_days', '1')), 0)
        except (TypeError, ValueError):
            value = 1
        unit = params.get_param('helper_sales.payment_pending_unit', 'days')
        if unit not in ('minutes', 'hours', 'days', 'weeks'):
            unit = 'days'
        return timedelta(**{unit: value}), "%s %s" % (value, unit)

    def action_generate_product_references(self):
        """Inazalisha Internal Reference kwa bidhaa zisizo na code kwa mfululizo tofauti wa kila kategoria."""
        products = self.env['product.template'].search(
            ['|', ('default_code', '=', False), ('default_code', '=', ''), ('categ_id', '!=', False)],
            order='categ_id, id',
        )

        count = 0
        for product in products:
            generated_ref = product.categ_id.generate_next_product_reference()
            if generated_ref:
                product.write({'default_code': generated_ref})
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