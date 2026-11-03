# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class LdsAllocation(models.Model):
    _name = 'lds.allocation'
    _inherit = ['mail.thread']
    _description = 'Interest & Principal Allocation per Company'
    _order = 'date, id'

    distribution_id = fields.Many2one('lds.loan.distribution', required=True, ondelete='cascade', index=True)
    loan_id = fields.Many2one(related='distribution_id.loan_id', store=True)
    company_id = fields.Many2one(related='distribution_id.company_id', store=True, string='Treasury Company')
    target_company_id = fields.Many2one(related='distribution_id.target_company_id', store=True,
                                        string='Company')
    currency_id = fields.Many2one(related='distribution_id.currency_id')
    line_id = fields.Many2one('lds.bank.loan.line', string='Schedule Line', ondelete='cascade')
    date = fields.Date(required=True)
    principal_share = fields.Monetary(string='Principal')
    interest_share = fields.Monetary(string='Bank Interest')
    markup_share = fields.Monetary(string='Markup')
    total_share = fields.Monetary(compute='_compute_total', store=True, string='Total')
    state = fields.Selection([('draft', 'Draft'), ('accrued', 'Interest Accrued'), ('paid', 'Settled')],
                             default='draft', tracking=True)
    settle_date = fields.Date(readonly=True)
    hq_move_id = fields.Many2one('account.move', readonly=True, copy=False, string='Treasury Accrual')
    target_move_id = fields.Many2one('account.move', readonly=True, copy=False, string='Company Accrual')
    settle_hq_move_id = fields.Many2one('account.move', readonly=True, copy=False, string='Treasury Settlement')
    settle_target_move_id = fields.Many2one('account.move', readonly=True, copy=False,
                                            string='Company Settlement')

    @api.depends('principal_share', 'interest_share', 'markup_share')
    def _compute_total(self):
        for a in self:
            a.total_share = a.principal_share + a.interest_share + a.markup_share

    def action_accrue(self):
        """Charge the interest (bank interest + markup) to the receiving company."""
        for a in self:
            if a.state != 'draft':
                continue
            d = a.distribution_id
            hq, tgt = d.company_id, d.target_company_id
            interest_total = a.interest_share + a.markup_share
            if d.loan_id.post_entries and interest_total:
                hqc = hq._lds_cfg(['lds_receivable_account_id', 'lds_interest_income_account_id'])
                tc = tgt._lds_cfg(['lds_payable_account_id', 'lds_interest_expense_account_id'])
                label = _("Interest %(loan)s %(date)s - %(c)s", loan=d.loan_id.name, date=a.date, c=tgt.name)
                a.hq_move_id = hq._lds_post_move(a.date, label, [
                    (hqc['lds_receivable_account_id'], interest_total, 0.0, label, tgt.partner_id),
                    (hqc['lds_interest_income_account_id'], 0.0, interest_total, label, tgt.partner_id),
                ])
                a.target_move_id = tgt._lds_post_move(a.date, label, [
                    (tc['lds_interest_expense_account_id'], interest_total, 0.0, label, hq.partner_id),
                    (tc['lds_payable_account_id'], 0.0, interest_total, label, hq.partner_id),
                ])
            a.state = 'accrued'
        return True

    def action_settle(self):
        """The receiving company pays principal + interest back to the treasury."""
        for a in self:
            if a.state != 'accrued':
                raise UserError(_("Accrue the interest before settling."))
            d = a.distribution_id
            hq, tgt = d.company_id, d.target_company_id
            if d.loan_id.post_entries and a.total_share:
                hq_cash = hq._lds_cash_account()
                hq_rec = hq._lds_cfg(['lds_receivable_account_id'])['lds_receivable_account_id']
                tgt_cash = tgt._lds_cash_account()
                tgt_pay = tgt._lds_cfg(['lds_payable_account_id'])['lds_payable_account_id']
                today = fields.Date.context_today(self)
                label = _("Repayment from %(c)s - %(loan)s", c=tgt.name, loan=d.loan_id.name)
                a.settle_hq_move_id = hq._lds_post_move(today, label, [
                    (hq_cash, a.total_share, 0.0, label, tgt.partner_id),
                    (hq_rec, 0.0, a.total_share, label, tgt.partner_id),
                ])
                a.settle_target_move_id = tgt._lds_post_move(today, label, [
                    (tgt_pay, a.total_share, 0.0, label, hq.partner_id),
                    (tgt_cash, 0.0, a.total_share, label, hq.partner_id),
                ])
            a.write({'state': 'paid', 'settle_date': fields.Date.context_today(self)})
        return True
