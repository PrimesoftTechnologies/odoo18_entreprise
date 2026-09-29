{
    'name': 'HR Expense Control Number',
    'version': '1.0',
    'summary': 'Track a Control Number on expenses, expense reports and payments',
    'category': 'Human Resources/Expenses',
    'depends': ['hr_expense'],
    'data': [
        'views/hr_expense_views.xml',
        'views/hr_expense_sheet_views.xml',
        'views/account_payment_register_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
