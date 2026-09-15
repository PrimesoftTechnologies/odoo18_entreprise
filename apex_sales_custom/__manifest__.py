{
    'name': 'Apex Sales Customizations',
    'version': '18.0.2.0.0',
    'category': 'Sales/Sales',
    'summary': 'Track quantity changes and delete reasons with wizard popup on sales order lines.',
    'depends': ['sale'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/sale_order_line_delete_wizard_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}