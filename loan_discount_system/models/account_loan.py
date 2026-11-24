# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountLoan(models.Model):
    """Accounting > Loans: show the customers (Discount Centers) that received money from this bank loan."""
    _inherit = 'account.loan'

    lds_distributor_ids = fields.Many2many(
        'lds.customer.loan', string='Loan Distributors', compute='_compute_lds_distributor_ids',
        help="All customers (distributions) that receive money from this bank loan.")

    def _compute_lds_distributor_ids(self):
        Distribution = self.env['lds.customer.loan'].sudo()
        for loan in self:
            loan_id = loan._origin.id or loan.id
            if loan_id:
                loan.lds_distributor_ids = Distribution.search([
                    ('odoo_loan_model', '=', loan._name),
                    ('odoo_loan_id', '=', loan_id),
                ], order='date, id')
            else:
                loan.lds_distributor_ids = False
