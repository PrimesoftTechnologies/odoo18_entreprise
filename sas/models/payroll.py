# -*- coding: utf-8 -*-

from odoo import models, fields

class HrContract(models.Model):
    _inherit = 'hr.contract'

    reimbursement_amount_add = fields.Monetary(
        string="Reimbursement Amount",
        help="Reimbursement to be added to employee net salary."
    )

    is_nssf = fields.Boolean(
        string="NSSF",
        default=True,
        help="Indicates if the contract include nssf."
    )

    is_paye = fields.Boolean(
        string="PAYE",
        default=True,
        help="Indicates if the contract include paye."
    )
    is_wcf = fields.Boolean(
        string="WCF", 
        help="Indicates if the contract include wcf."
    )
    is_nhif = fields.Boolean(
        string="NHIF",
        help="Indicates if the contract include nhif."
    )
    is_sdl = fields.Boolean(
        string="SDL",
        help="Indicates if the contract include sdl."
    )   
    is_paye_secondary = fields.Boolean(
        string="PAYE Secondary",
        help="Indicates if the contract include paye secondary."
    )
    is_retired = fields.Boolean(
        string="Retired",
        help="Indicates if the employee is retired."
    )
    is_withholding_tax = fields.Boolean(
        string="Withholding Tax",
        help="Indicates if the contract include withholding tax."
    )
    is_loan_board = fields.Boolean(
        string="Loan Board",
        help="Indicates if the contract include loan board."
    )
