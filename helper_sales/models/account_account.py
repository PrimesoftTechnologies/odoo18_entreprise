# -*- coding: utf-8 -*-

from odoo import api, fields, models


class AccountAccount(models.Model):
    _inherit = 'account.account'

    analytic_account_id = fields.Many2one(
        'account.analytic.account', string='Analytic Account', copy=False, ondelete='set null',
        help="Analytic account linked to this ledger. It is created automatically when the ledger is created.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        accounts = super().create(vals_list)
        if not self.env.context.get('install_mode') and not self.env.context.get('skip_analytic_link'):
            for account in accounts.filtered(lambda a: not a.analytic_account_id):
                account._link_analytic_account()
        return accounts

    def _link_analytic_account(self):
        self.ensure_one()
        code = self.code or ''
        vals = {
            'name': ('%s %s' % (code, self.name)).strip(),
            'code': code or False,
        }
        companies = self.company_ids if 'company_ids' in self._fields else self.company_id
        if len(companies) == 1:
            vals['company_id'] = companies.id
        # sudo: the person creating a ledger may not have analytic accounting rights
        self.analytic_account_id = self.env['account.analytic.account'].sudo().create(vals)
