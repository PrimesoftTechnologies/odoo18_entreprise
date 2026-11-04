# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class LdsAllocation(models.Model):
    _name = 'lds.allocation'
    _inherit = ['mail.thread']
    _description = 'Interest & Principal Allocation per Discount Center'
    _order = 'date, id'

    distribution_id = fields.Many2one('lds.loan.distribution', required=True, ondelete='cascade', index=True)
    loan_id = fields.Many2one(related='distribution_id.loan_id', store=True)
    company_id = fields.Many2one(related='distribution_id.company_id', store=True, string='Treasury Company')
    partner_id = fields.Many2one(related='distribution_id.partner_id', store=True,
                                 string='Discount Center')
    currency_id = fields.Many2one(related='distribution_id.currency_id')
    line_id = fields.Many2one('lds.bank.loan.line', string='Schedule Line', ondelete='cascade')
    date = fields.Date(required=True)
    principal_share = fields.Monetary(string='Principal')
    interest_share = fields.Monetary(string='Bank Interest')
    markup_share = fields.Monetary(string='Markup')
    total_share = fields.Monetary(compute='_compute_total', store=True, string='Total')
    state = fields.Selection([('draft', 'Draft'), ('accrued', 'Interest Accrued'), ('paid', 'Settled')],
                             default='draft', tracking=True)
    balance_after = fields.Monetary(compute='_compute_balance_after', string='Principal Balance After')
    settle_date = fields.Date(readonly=True)
    accrue_move_id = fields.Many2one('account.move', readonly=True, copy=False, string='Accrual Entry')
    settle_move_id = fields.Many2one('account.move', readonly=True, copy=False, string='Settlement Entry')

    @api.depends('principal_share', 'interest_share', 'markup_share')
    def _compute_total(self):
        for a in self:
            a.total_share = a.principal_share + a.interest_share + a.markup_share

    @api.depends('distribution_id.amount', 'distribution_id.allocation_ids.principal_share')
    def _compute_balance_after(self):
        for a in self:
            siblings = a.distribution_id.allocation_ids.filtered(
                lambda x: (x.date, x.id) <= (a.date, a.id))
            a.balance_after = a.distribution_id.amount - sum(siblings.mapped('principal_share'))

    @api.depends('loan_id.name', 'partner_id.name', 'date')
    def _compute_display_name(self):
        for a in self:
            a.display_name = "%s - %s - %s" % (a.loan_id.name or '', a.partner_id.name or '', a.date or '')

    def action_accrue(self):
        """Charge the interest (bank interest + markup) to the Discount Center (customer)."""
        for a in self:
            if a.state != 'draft':
                continue
            d = a.distribution_id
            loan = d.loan_id
            interest_total = a.interest_share + a.markup_share
            if loan.post_entries and interest_total:
                company = loan.company_id
                journal = loan._lds_journal()
                receivable = company._lds_receivable(d.partner_id)
                income = company._lds_cfg(['lds_interest_income_account_id'])['lds_interest_income_account_id']
                label = _("Interest %(loan)s %(date)s - %(c)s", loan=loan.name, date=a.date, c=d.partner_id.name)
                # Dr Customer receivable / Cr Interest income
                a.accrue_move_id = company._lds_post_move(journal, a.date, label, [
                    (receivable, interest_total, 0.0, label, d.partner_id),
                    (income, 0.0, interest_total, label, d.partner_id),
                ])
            a.state = 'accrued'
        return True

    def action_settle(self):
        """The Discount Center pays principal + interest to the treasury."""
        for a in self:
            if a.state != 'accrued':
                raise UserError(_("Accrue the interest before settling."))
            d = a.distribution_id
            loan = d.loan_id
            today = fields.Date.context_today(self)
            if loan.post_entries and a.total_share:
                company = loan.company_id
                journal = loan._lds_journal()
                receivable = company._lds_receivable(d.partner_id)
                label = _("Repayment from %(c)s - %(loan)s", c=d.partner_id.name, loan=loan.name)
                # Dr Bank / Cr Customer receivable
                a.settle_move_id = company._lds_post_move(journal, today, label, [
                    (journal.default_account_id, a.total_share, 0.0, label, d.partner_id),
                    (receivable, 0.0, a.total_share, label, d.partner_id),
                ])
            a.write({'state': 'paid', 'settle_date': today})
        return True
