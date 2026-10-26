{
    'name': 'Fred Phone Store Application',
    'version': '18.0.1.0.3',
    'category': 'Sales/Point of Sale',
    'summary': 'Simple Profit & Loss report for phone shops inside Point of Sale',
    'description': """
Simple Profit and Loss for a phone store
========================================
* Sales Price  - Cost Price  = Profit (Gross)
* Profit - Expenses = Net Profit
* Added under Point of Sale > Reporting > Profit and Loss
* Simple Store Expenses (rent, salaries, electricity, transport...)
* Filter by date and by shop, print as PDF
    """,
    'author': 'Fred',
    'license': 'LGPL-3',
    'depends': ['point_of_sale'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/expense_type_data.xml',
        'report/pl_report_templates.xml',
        'views/expense_type_views.xml',
        'views/store_expense_views.xml',
        'views/pl_report_wizard_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': False,
}
