# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import UserError


class ResCompany(models.Model):
    _inherit = 'res.company'

    lds_journal_id = fields.Many2one(
        'account.journal', string='Default Loan Journal',
        domain="[('company_id', '=', id), ('type', 'in', ('bank', 'cash'))]",
        help="One bank/cash journal used for all entries (can be changed on each loan).")
    lds_interest_income_account_id = fields.Many2one(
        'account.account', string='Interest Income Account',
        domain="[('company_ids', 'in', id)]",
        help="Credited with the interest paid by the customers (Discount Centers).")

    _LDS_LABELS = {
        'lds_interest_income_account_id': 'Interest Income Account',
    }

    def _lds_cfg(self, keys):
        self.ensure_one()
        company = self.sudo()
        missing = [self._LDS_LABELS[k] for k in keys if not company[k]]
        if missing:
            raise UserError(_(
                "Company '%(company)s' is missing Loan Discount settings: %(missing)s.\n"
                "Go to Loan Discount System > Configuration > Company Settings.",
                company=company.name, missing=', '.join(missing)))
        return {k: company[k] for k in keys}

    def _lds_receivable(self, partner):
        """Receivable account of the customer (Discount Center)."""
        self.ensure_one()
        account = partner.sudo().with_company(self.sudo()).property_account_receivable_id
        if not account:
            raise UserError(_("Customer '%s' has no Receivable account.", partner.name))
        return account

    def _lds_post_move(self, journal, date, ref, lines):
        """lines: list of (account, debit, credit, label, partner)."""
        self.ensure_one()
        company = self.sudo()
        line_vals = []
        for account, debit, credit, label, partner in lines:
            if not debit and not credit:
                continue
            line_vals.append((0, 0, {
                'account_id': account.id, 'debit': debit, 'credit': credit,
                'name': label, 'partner_id': partner.id if partner else False,
            }))
        move = self.env['account.move'].sudo().with_company(company).create({
            'move_type': 'entry', 'date': date, 'ref': ref,
            'journal_id': journal.id, 'company_id': company.id, 'line_ids': line_vals,
        })
        move.action_post()
        return move
