{
    'name': 'Approval Manufacturing Custom',
    'version': '18.0.1.0.0',
    'category': 'Manufacturing/Manufacturing',
    'sequence': -16,
    'summary': 'Custom approval and inspection workflow for Manufacturing Orders',
    'author': 'PrimeSoft Technologies Property',
    'depends': ['mrp', 'base'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/res_company_views.xml',
        'views/mrp_production_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}