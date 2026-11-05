# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class LdsCustomerLoanLine(models.Model):
    _name = 'lds.customer.loan.line'
    _description = 'Customer Loan Amortization Line'
    _order = 'loan_id, date, id'

    loan_id = fields.Many2one('lds.customer.loan', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one(related='loan_id.company_id', store=True)
    currency_id = fields.Many2one(related='loan_id.currency_id')
    number = fields.Integer(string='#')
    date = fields.Date(required=True)
    principal = fields.Monetary(string='Principals')
    interest = fields.Monetary(string='Interests')
    payment = fields.Monetary(string='Payments', compute='_compute_payment', store=True)
    balance = fields.Monetary(string='Outstanding Balance')
    status = fields.Selection([('unpaid', 'Unpaid'), ('paid', 'Paid')], default='unpaid', copy=False)
    paid_date = fields.Date(readonly=True, copy=False)
    move_id = fields.Many2one('account.move', string='Payment Entry', readonly=True, copy=False)

    @api.depends('principal', 'interest')
    def _compute_payment(self):
        for line in self:
            line.payment = line.principal + line.interest

    def action_pay(self):
        """The customer pays this installment: Dr Bank / Cr Receivable (principal) / Cr Interest income."""
        for line in self:
            loan = line.loan_id
            if loan.state != 'running':
                raise UserError(_("The loan must be Running to register a payment."))
            if line.status == 'paid':
                continue
            today = fields.Date.context_today(self)
            if loan.post_entries and line.payment:
                company = loan.company_id
                journal = loan._lds_journal()
                receivable = company._lds_receivable(loan.partner_id)
                label = _("Payment %(n)s - %(loan)s (%(c)s)", n=line.number, loan=loan.name, c=loan.partner_id.name)
                move_lines = [
                    (journal.default_account_id, line.payment, 0.0, label, loan.partner_id),
                    (receivable, 0.0, line.principal, label, loan.partner_id),
                ]
                if line.interest:
                    income = company._lds_cfg(['lds_interest_income_account_id'])['lds_interest_income_account_id']
                    move_lines.append((income, 0.0, line.interest, label, loan.partner_id))
                line.move_id = company._lds_post_move(journal, today, label, move_lines)
            line.write({'status': 'paid', 'paid_date': today})
            if all(l.status == 'paid' for l in loan.line_ids):
                loan.state = 'closed'
        return True
