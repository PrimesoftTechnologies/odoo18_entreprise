# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class LdsLoanDistribution(models.Model):
    _name = 'lds.loan.distribution'
    _inherit = ['mail.thread']
    _description = 'Loan Distribution to Discount Center'
    _order = 'date desc, id desc'

    loan_id = fields.Many2one('lds.bank.loan', string='Bank Loan', required=True, ondelete='cascade',
                              index=True, domain="[('state', '=', 'running')]")
    loan_undistributed = fields.Monetary(related='loan_id.undistributed', string='Still Available to Distribute')
    loan_outstanding = fields.Monetary(related='loan_id.outstanding_balance', string='Bank Loan Outstanding')
    company_id = fields.Many2one(related='loan_id.company_id', store=True, string='Treasury Company')
    currency_id = fields.Many2one(related='loan_id.currency_id')
    partner_id = fields.Many2one('res.partner', string='Discount Center (Customer)', required=True,
                                 tracking=True)
    date = fields.Date(required=True, default=fields.Date.context_today)
    amount = fields.Monetary(string='Amount Distributed', tracking=True)
    markup_rate = fields.Float(string='Markup (% p.a.)', digits=(12, 4),
                               help="Extra interest charged on top of the bank rate.")
    state = fields.Selection([('draft', 'Draft'), ('confirmed', 'Confirmed')], default='draft', tracking=True)
    move_id = fields.Many2one('account.move', string='Journal Entry', readonly=True, copy=False)
    allocation_ids = fields.One2many('lds.allocation', 'distribution_id')

    paid_principal = fields.Monetary(compute='_compute_balances', string='Principal Repaid')
    outstanding = fields.Monetary(compute='_compute_balances', string='Outstanding Principal')
    interest_charged = fields.Monetary(compute='_compute_balances', string='Interest Charged')
    amount_due = fields.Monetary(compute='_compute_balances', string='Accrued & Unpaid')
    total_principal = fields.Monetary(compute='_compute_balances', string='Total Principal to Repay')
    total_bank_interest = fields.Monetary(compute='_compute_balances', string='Total Bank Interest')
    total_markup = fields.Monetary(compute='_compute_balances', string='Total Markup')
    total_payable = fields.Monetary(compute='_compute_balances', string='Total to Pay Treasury')

    _sql_constraints = [
        ('unique_partner_loan', 'unique(loan_id, partner_id)',
         'A Discount Center can only appear once per loan. Edit the existing distribution instead.'),
    ]

    @api.onchange('loan_id')
    def _onchange_loan_id(self):
        if self.loan_id and not self.amount:
            self.amount = self.loan_id.undistributed

    @api.depends('loan_id.name', 'partner_id.name')
    def _compute_display_name(self):
        for d in self:
            d.display_name = "%s - %s" % (d.loan_id.name or '', d.partner_id.name or '')

    @api.depends('amount', 'state', 'allocation_ids.state', 'allocation_ids.total_share', 'allocation_ids.principal_share',
                 'allocation_ids.interest_share', 'allocation_ids.markup_share')
    def _compute_balances(self):
        for d in self:
            paid = d.allocation_ids.filtered(lambda a: a.state == 'paid')
            accrued = d.allocation_ids.filtered(lambda a: a.state == 'accrued')
            charged = d.allocation_ids.filtered(lambda a: a.state in ('accrued', 'paid'))
            d.paid_principal = sum(paid.mapped('principal_share'))
            d.outstanding = d.amount - d.paid_principal if d.state == 'confirmed' else 0.0
            d.interest_charged = sum(charged.mapped('interest_share')) + sum(charged.mapped('markup_share'))
            d.amount_due = sum(accrued.mapped('total_share'))
            d.total_principal = sum(d.allocation_ids.mapped('principal_share'))
            d.total_bank_interest = sum(d.allocation_ids.mapped('interest_share'))
            d.total_markup = sum(d.allocation_ids.mapped('markup_share'))
            d.total_payable = sum(d.allocation_ids.mapped('total_share'))

    def action_confirm(self):
        for d in self:
            loan = d.loan_id
            if d.state != 'draft':
                continue
            if loan.state != 'running':
                raise UserError(_("Confirm the bank loan first (it must be Running)."))
            if d.amount <= 0:
                raise UserError(_("Enter the amount to distribute."))
            others = sum(loan.distribution_ids.filtered(
                lambda x: x.state == 'confirmed' and x.id != d.id).mapped('amount'))
            if loan.currency_id.compare_amounts(others + d.amount, loan.principal) > 0:
                raise UserError(_("Total distribution (%(t)s) exceeds the loan amount (%(p)s).",
                                  t=others + d.amount, p=loan.principal))
            if loan.post_entries:
                company = loan.company_id
                journal = loan._lds_journal()
                receivable = company._lds_receivable(d.partner_id)
                label = _("Loan %(loan)s distributed to %(c)s", loan=loan.name, c=d.partner_id.name)
                # Dr Customer receivable / Cr Bank
                d.move_id = company._lds_post_move(journal, d.date, label, [
                    (receivable, d.amount, 0.0, label, d.partner_id),
                    (journal.default_account_id, 0.0, d.amount, label, d.partner_id),
                ])
            d.state = 'confirmed'
            d._generate_allocations()
        return True

    def _generate_allocations(self):
        """Compute what the Discount Center must pay each month (its share of the bank schedule).

        share % = amount distributed / bank loan amount
        principal = bank principal x share %
        bank interest = bank interest x share %
        markup = (bank balance before payment x share %) x markup / 12
        """
        Allocation = self.env['lds.allocation']
        for d in self:
            loan = d.loan_id
            if d.state != 'confirmed' or loan.principal <= 0:
                continue
            cur = loan.currency_id
            pct = d.amount / loan.principal
            lines = (loan.line_ids - d.allocation_ids.mapped('line_id')).sorted(lambda l: (l.date, l.id))
            vals = []
            for line in lines:
                balance_before = line.balance + line.principal
                vals.append({
                    'distribution_id': d.id,
                    'line_id': line.id,
                    'date': line.date,
                    'principal_share': cur.round(line.principal * pct),
                    'interest_share': cur.round(line.interest * pct),
                    'markup_share': cur.round(balance_before * pct * d.markup_rate / 100.0 / 12.0),
                })
            if vals:
                Allocation.create(vals)
            # rounding: the principal repaid must equal the amount distributed
            allocs = d.allocation_ids.sorted(lambda a: (a.date, a.id))
            if allocs and allocs[-1].state == 'draft':
                diff = cur.round(d.amount - sum(allocs.mapped('principal_share')))
                if diff:
                    allocs[-1].principal_share += diff
        return True

    def action_recompute(self):
        """Rebuild the not-yet-accrued months (use after the bank schedule or markup changed)."""
        for d in self:
            d.allocation_ids.filtered(lambda a: a.state == 'draft').unlink()
            d._generate_allocations()
        return True

    def unlink(self):
        if self.filtered(lambda d: d.state == 'confirmed'):
            raise UserError(_("Confirmed distributions cannot be deleted."))
        return super().unlink()
