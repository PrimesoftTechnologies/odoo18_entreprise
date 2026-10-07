# -*- coding: utf-8 -*-
{
    'name': "SAS Invoice PO",
    'summary': "Adds PO No search, filter & list column to Customer Invoices",
    'description': """
SAS Invoice PO
==============
Enhances the existing 'po_no' field (from sas module) on Customer Invoices:

  - Search invoices by PO No (from search bar)
  - Quick filter: 'Has PO No'
  - Group By: PO No
  - Show PO No column in invoice list view
  - Print PO No on PDF invoice
    """,
    'author': "Aziz Msami",
    'company': 'Primesoft Technologies Limited',
    'website': "https://www.primesoft.co.tz",
    'category': 'Accounting/Accounting',
    'version': '17.0.1.0.0',
    'depends': ['account', 'sas'],
    'data': [
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'AGPL-3',
}