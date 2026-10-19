{
    'name': 'Payslip Attendance BIC',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Record employee attendance and pull worked days into payslips',
    'description': """
Adds an "Attendance" submenu under Payroll > Payslips where you record
Employee, Date and Time. On a payslip, once the Employee and Period are
set, the days attended within the period are pulled in automatically as a
worked days line (code ATTBIC) and listed in an "Attendance (BIC)" tab.
    """,
    'author': 'BIC',
    'depends': ['hr', 'hr_payroll'],
    'data': [
        'security/ir.model.access.csv',
        'data/work_entry_type_data.xml',
        'views/attendance_views.xml',
        'views/hr_payslip_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
