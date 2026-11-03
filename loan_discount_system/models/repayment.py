# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class LdsBankLoanRepayment(models.Model):
    _name = 'lds.bank.loan.repayment'
    _inherit = ['mail.thread']
    _description = 'Bank Loan Repayment'
    _order = 'date desc, id desc'

    name = fields.Char(readonly=True, copy=False, default='New')
    loan_id = fields.Many2one('lds.bank.loan', required=True, ondelete='cascade', index=True,
                              domain=[('state', '=', 'running')])
    company_id = fields.Many2one(related='loan_id.company_id', store=True)
    currency_id = fields.Many2one(related='loan_id.currency_id')
    line_id = fields.Many2one('lds.bank.loan.line', string='Schedule Line',
                              domain="[('loan_id', '=', loan_id)]")
    date = fields.Date(required=True, default=fields.Date.context_today)
    principal_amount = fields.Monetary(string='Principal')
    interest_amount = fields.Monetary(string='Interest')
    total_amount = fields.Monetary(compute='_compute_total', store=True, string='Total Paid')
    balance_after = fields.Monetary(string='Outstanding After', readonly=True)
    state = fields.Selection([('draft', 'Draft'), ('posted', 'Posted')], default='draft', tracking=True)
    move_id = fields.Many2one('account.move', string='Journal Entry', readonly=True, copy=False)
    notes = fields.Char()

    @api.depends('principal_amount', 'interest_amount')
    def _compute_total(self):
        for rec in self:
            rec.total_amount = rec.principal_amount + rec.interest_amount

    @api.constrains('principal_amount', 'interest_amount')
    def _check_amounts(self):
        for rec in self:
            if rec.principal_amount < 0 or rec.interest_amount < 0:
                raise ValidationError(_("Amounts cannot be negative."))

    @api.onchange('line_id')
    def _onchange_line_id(self):
        if self.line_id:
            self.principal_amount = self.line_id.principal
            self.interest_amount = self.line_id.interest
            self.date = self.line_id.date

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('lds.bank.loan.repayment') or 'New'
        return super().create(vals_list)

    def action_post(self):
        for rec in self:
            loan = rec.loan_id
            if rec.state != 'draft':
                continue
            if loan.state != 'running':
                raise UserError(_("The loan must be Running to register repayments."))
            if rec.total_amount <= 0:
                raise UserError(_("Enter a repayment amount."))
            if loan.currency_id.compare_amounts(rec.principal_amount, loan.outstanding_balance) > 0:
                raise UserError(_("Principal exceeds the outstanding balance (%s).", loan.outstanding_balance))
            if loan.post_entries:
                company = loan.company_id
                cash = company._lds_cash_account()
                cfg = company._lds_cfg(['lds_loan_account_id', 'lds_interest_expense_account_id'])
                label = _("Repayment %(ref)s - %(loan)s", ref=rec.name, loan=loan.name)
                rec.move_id = company._lds_post_move(rec.date, label, [
                    (cfg['lds_loan_account_id'], rec.principal_amount, 0.0, label, loan.bank_id),
                    (cfg['lds_interest_expense_account_id'], rec.interest_amount, 0.0, label, loan.bank_id),
                    (cash, 0.0, rec.total_amount, label, loan.bank_id),
                ])
            rec.state = 'posted'
            rec.balance_after = loan.outstanding_balance
        return True

    def action_reset(self):
        for rec in self:
            if rec.move_id:
                move = rec.move_id.sudo()
                move.button_draft()
                move.unlink()
            rec.write({'state': 'draft', 'balance_after': 0.0})
        return True

    def unlink(self):
        if self.filtered(lambda r: r.state == 'posted'):
            raise UserError(_("Reset posted repayments to draft before deleting."))
        return super().unlink()
