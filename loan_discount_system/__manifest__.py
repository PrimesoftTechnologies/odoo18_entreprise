# -*- coding: utf-8 -*-
{
    'name': 'Loan Discount System',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Treasury bank loans, distribution to group companies, interest allocation and repayments',
    'description': """
Loan Discount System
====================
* Treasurer registers loans taken from banks (e.g. KCB) and links them to the Odoo Loan record
* Amortization schedule: computed (annuity / flat / equal principal) or uploaded from Excel (bank schedule)
* Repayments with running outstanding balance and accounting entries
* Distribution of the loan to group companies (Discount Center 1, 2, ...)
* Interest allocation per company (bank interest + optional markup), accrual and settlement
* Reconciliation against the outstanding balance of the Odoo Loan record
    """,
    'author': 'Primesoft',
    'depends': ['base', 'account', 'mail'],
    'external_dependencies': {'python': ['openpyxl']},
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'wizard/upload_wizard_views.xml',
        'views/bank_loan_views.xml',
        'views/repayment_views.xml',
        'views/distribution_views.xml',
        'views/allocation_views.xml',
        'views/res_company_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
