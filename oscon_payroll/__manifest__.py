{
    'name': 'OSCON Payroll',
    'version': '18.0.1.0.0',
    'summary': 'Adds a Non-Resident flag on contracts, toggled from payroll settings',
    'category': 'Human Resources/Payroll',
    'author': 'OSCON',
    'depends': ['hr_contract', 'hr_payroll'],
    'data': [
        'security/security.xml',
        'views/hr_contract_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
