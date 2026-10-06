# -*- coding: utf-8 -*-
{
    'name': "sas",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "Julius John Kanyenye",
    'company': 'Primesoft Technologies Limited',
    'website': "https://www.primesoft.co.tz",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','account','stock','hr_expense','fleet'],
    'external_dependencies': {
        'python': ['xlsxwriter'],
    },
    # always loaded
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'views/clearance.xml',
        'views/clearance_reimbursement_views.xml', 
        'views/shipping.xml',
        'views/configuration.xml',
        'views/transport.xml',
        'views/templates.xml',
        'views/fleet.xml',
        'views/expenses.xml',
        'views/sales.xml',
        'views/invoice.xml',
        'views/payroll.xml',
        'views/shipping_order_report_views.xml',
        'data/sequences.xml',
        'reports/headerfooter.xml',
        'reports/reimbursement.xml',
        'reports/quotation.xml',
        'wizard/clearance_report_wizard_views.xml',
        'reports/clearance_report_qweb.xml',
        'reports/financial_report_views.xml',
        'reports/transport_report_views.xml',

        # 'reports/delivery.xml',
        'reports/invoice.xml',
        'views/menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'sas/static/src/js/dashboard/sas_dashboard.js',
            'sas/static/src/xml/sas_dashboard.xml',
            'sas/static/src/scss/sas_dashboard.scss',
        ],
    },
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,
}

