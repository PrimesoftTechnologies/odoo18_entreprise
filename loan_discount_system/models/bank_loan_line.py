# -*- coding: utf-8 -*-
from odoo import api, fields, models


class LdsBankLoanLine(models.Model):
    _name = 'lds.bank.loan.line'
    _description = 'Bank Loan Amortization Line'
    _order = 'loan_id, date, id'

    loan_id = fields.Many2one('lds.bank.loan', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one(related='loan_id.company_id', store=True)
    currency_id = fields.Many2one(related='loan_id.currency_id')
    number = fields.Integer(string='#')
    date = fields.Date(required=True)
    principal = fields.Monetary(string='Principals')
    interest = fields.Monetary(string='Interests')
    payment = fields.Monetary(string='Payments', compute='_compute_payment', store=True)
    balance = fields.Monetary(string='Outstanding Balance')
    repayment_ids = fields.One2many('lds.bank.loan.repayment', 'line_id')
    paid_amount = fields.Monetary(compute='_compute_status', store=True)
    status = fields.Selection([('unpaid', 'Unpaid'), ('partial', 'Partial'), ('paid', 'Paid')],
                              compute='_compute_status', store=True)

    @api.depends('principal', 'interest')
    def _compute_payment(self):
        for line in self:
            line.payment = line.principal + line.interest

    @api.depends('repayment_ids.state', 'repayment_ids.total_amount', 'payment')
    def _compute_status(self):
        for line in self:
            paid = sum(line.repayment_ids.filtered(lambda r: r.state == 'posted').mapped('total_amount'))
            line.paid_amount = paid
            if paid and paid >= line.payment - 0.005:
                line.status = 'paid'
            elif paid:
                line.status = 'partial'
            else:
                line.status = 'unpaid'

    def action_register_payment(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Register Repayment',
            'res_model': 'lds.bank.loan.repayment',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_loan_id': self.loan_id.id,
                'default_line_id': self.id,
                'default_date': self.date,
                'default_principal_amount': self.principal,
                'default_interest_amount': self.interest,
            },
        }
