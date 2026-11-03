# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class LdsLoanDistribution(models.Model):
    _name = 'lds.loan.distribution'
    _inherit = ['mail.thread']
    _description = 'Loan Distribution to Group Company'
    _order = 'date desc, id desc'

    loan_id = fields.Many2one('lds.bank.loan', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one(related='loan_id.company_id', store=True, string='Treasury Company')
    currency_id = fields.Many2one(related='loan_id.currency_id')
    target_company_id = fields.Many2one('res.company', string='Receiving Company', required=True,
                                        domain="[('id', '!=', company_id)]", tracking=True)
    date = fields.Date(required=True, default=fields.Date.context_today)
    amount = fields.Monetary(string='Amount Distributed', tracking=True)
    markup_rate = fields.Float(string='Markup (% p.a.)', digits=(12, 4),
                               help="Extra interest charged on top of the bank rate.")
    state = fields.Selection([('draft', 'Draft'), ('confirmed', 'Confirmed')], default='draft', tracking=True)
    move_id = fields.Many2one('account.move', string='Treasury Entry', readonly=True, copy=False)
    target_move_id = fields.Many2one('account.move', string='Company Entry', readonly=True, copy=False)
    allocation_ids = fields.One2many('lds.allocation', 'distribution_id')

    paid_principal = fields.Monetary(compute='_compute_balances', string='Principal Repaid')
    outstanding = fields.Monetary(compute='_compute_balances', string='Outstanding Principal')
    interest_charged = fields.Monetary(compute='_compute_balances', string='Interest Charged')
    amount_due = fields.Monetary(compute='_compute_balances', string='Accrued & Unpaid')

    _sql_constraints = [
        ('unique_company_loan', 'unique(loan_id, target_company_id)',
         'A company can only appear once per loan. Edit the existing distribution instead.'),
    ]

    @api.depends('amount', 'state', 'allocation_ids.state', 'allocation_ids.principal_share',
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
                hq, tgt = loan.company_id, d.target_company_id
                hq_cash = hq._lds_cash_account()
                hq_rec = hq._lds_cfg(['lds_receivable_account_id'])['lds_receivable_account_id']
                tgt_cash = tgt._lds_cash_account()
                tgt_pay = tgt._lds_cfg(['lds_payable_account_id'])['lds_payable_account_id']
                label = _("Loan distribution %(loan)s -> %(c)s", loan=loan.name, c=tgt.name)
                d.move_id = hq._lds_post_move(d.date, label, [
                    (hq_rec, d.amount, 0.0, label, tgt.partner_id),
                    (hq_cash, 0.0, d.amount, label, tgt.partner_id),
                ])
                d.target_move_id = tgt._lds_post_move(d.date, label, [
                    (tgt_cash, d.amount, 0.0, label, hq.partner_id),
                    (tgt_pay, 0.0, d.amount, label, hq.partner_id),
                ])
            d.state = 'confirmed'
        return True

    def unlink(self):
        if self.filtered(lambda d: d.state == 'confirmed'):
            raise UserError(_("Confirmed distributions cannot be deleted."))
        return super().unlink()
