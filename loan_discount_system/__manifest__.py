# -*- coding: utf-8 -*-
{
    'name': 'Loan Discount System',
    'version': '18.0.2.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Distribute a bank loan to customers (Discount Centers) with their own amortization schedule',
    'description': """
Loan Discount System
====================
The treasurer registers the bank loan in Accounting > Loans (untouched).
This module records the distribution of that money to customers (Discount Centers):

* Same layout as the Odoo Loan form: Amount Borrowed, Interest, Outstanding Balance,
  Loan Date, Duration, Amortization schedule, Loan Settings
* Confirm / Upload (Excel schedule) / Compute buttons
* Accounting entries on one journal: disbursement and customer payments
* Link to the bank loan of Accounting > Loans
    """,
    'author': 'Primesoft',
    'depends': ['base', 'account', 'mail'],
    'external_dependencies': {'python': ['openpyxl']},
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'wizard/upload_wizard_views.xml',
        'views/customer_loan_views.xml',
        'views/res_company_views.xml',
        'views/menus.xml',
        'data/restore.xml',
    ],
    'installable': True,
    'application': True,
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3',
}
