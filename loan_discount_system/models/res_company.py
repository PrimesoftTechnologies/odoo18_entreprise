# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import UserError


class ResCompany(models.Model):
    _inherit = 'res.company'

    lds_journal_id = fields.Many2one(
        'account.journal', string='Loan Journal',
        domain="[('company_id', '=', id), ('type', 'in', ('bank', 'cash'))]",
        help="Bank/Cash journal used for loan receipts, distributions, repayments and settlements.")
    lds_loan_account_id = fields.Many2one(
        'account.account', string='Bank Loan Payable Account',
        domain="[('company_ids', 'in', id)]",
        help="HQ (treasury) company: liability account where the bank loan principal is recorded.")
    lds_interest_expense_account_id = fields.Many2one(
        'account.account', string='Interest Expense Account',
        domain="[('company_ids', 'in', id)]")
    lds_interest_income_account_id = fields.Many2one(
        'account.account', string='Interest Recovery / Income Account',
        domain="[('company_ids', 'in', id)]",
        help="HQ: credited when interest is charged to the group companies.")
    lds_receivable_account_id = fields.Many2one(
        'account.account', string='Due from Group Companies (HQ)',
        domain="[('company_ids', 'in', id)]",
        help="HQ: inter-company receivable account.")
    lds_payable_account_id = fields.Many2one(
        'account.account', string='Due to HQ / Treasury (Subsidiary)',
        domain="[('company_ids', 'in', id)]",
        help="Subsidiary: inter-company payable account.")

    _LDS_LABELS = {
        'lds_journal_id': 'Loan Journal',
        'lds_loan_account_id': 'Bank Loan Payable Account',
        'lds_interest_expense_account_id': 'Interest Expense Account',
        'lds_interest_income_account_id': 'Interest Recovery / Income Account',
        'lds_receivable_account_id': 'Due from Group Companies (HQ)',
        'lds_payable_account_id': 'Due to HQ / Treasury (Subsidiary)',
    }

    def _lds_cfg(self, keys):
        """Return {key: record} for the Loan Discount settings of this company, or raise."""
        self.ensure_one()
        company = self.sudo()
        missing = [self._LDS_LABELS[k] for k in keys if not company[k]]
        if missing:
            raise UserError(_(
                "Company '%(company)s' is missing Loan Discount settings: %(missing)s.\n"
                "Go to Loan Discount System > Configuration > Company Settings.",
                company=company.name, missing=', '.join(missing)))
        return {k: company[k] for k in keys}

    def _lds_cash_account(self):
        self.ensure_one()
        journal = self._lds_cfg(['lds_journal_id'])['lds_journal_id']
        account = journal.default_account_id
        if not account:
            raise UserError(_("Journal '%s' has no default account.", journal.name))
        return account

    def _lds_post_move(self, date, ref, lines):
        """lines: list of (account, debit, credit, label, partner)."""
        self.ensure_one()
        company = self.sudo()
        journal = self._lds_cfg(['lds_journal_id'])['lds_journal_id']
        line_vals = []
        for account, debit, credit, label, partner in lines:
            if not debit and not credit:
                continue
            line_vals.append((0, 0, {
                'account_id': account.id,
                'debit': debit,
                'credit': credit,
                'name': label,
                'partner_id': partner.id if partner else False,
            }))
        move = self.env['account.move'].sudo().with_company(company).create({
            'move_type': 'entry',
            'date': date,
            'ref': ref,
            'journal_id': journal.id,
            'company_id': company.id,
            'line_ids': line_vals,
        })
        move.action_post()
        return move
