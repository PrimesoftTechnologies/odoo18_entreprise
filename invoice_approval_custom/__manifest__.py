{
    'name': 'Invoice Approval Custom',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Accounting',
    'sequence':-19,
    'summary': 'Adds an approval workflow before confirming invoices with company settings.',
    'author': 'Custom',
    'depends': ['account', 'sale'],
    'data': [
        'views/res_config_settings_views.xml',
        'views/account_move_views.xml',
        'reports/account_move_report_inherit.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}