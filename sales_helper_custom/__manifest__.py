{
    'name': 'Sales Helper Custom',
    'version': '18.0.1.0.0',
    'sequence':-23,
    'summary': 'Adds a Helper field to Sale Orders under Salesperson',
    'category': 'Sales',
    'author': 'Custom',
    'depends': ['sale'],
    'data': [
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
