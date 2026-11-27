{
    'name': 'Meals Attendance Management',
    'version': '18.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Record employee meals attendance per customer, report and invoice customers',
    'description': """
Meals Attendance Management
===========================
* Customers (res.partner) with their own employees (hr.employee) and departments (hr.department)
* Meal types configurable per customer (with price)
* Import attendance-machine logs (Excel): meal detected from scan time, sheets created automatically
* Import customer employees from CSV / XLSX
* Pivot / graph analysis and PDF customer statement
* Generate customer invoices (account.move) from confirmed attendance
    """,
    'author': 'Your Company',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'hr', 'account'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/meals_type_views.xml',
        'views/meals_attendance_views.xml',
        'views/customer_employee_views.xml',
        'wizard/employee_import_wizard_views.xml',
        'wizard/log_import_wizard_views.xml',
        'wizard/invoice_wizard_views.xml',
        'wizard/report_wizard_views.xml',
        'report/customer_statement_templates.xml',
        'views/menus.xml',
    ],
    'application': True,
    'installable': True,
}
