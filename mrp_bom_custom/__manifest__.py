{
    'name': 'MRP BoM Customization',
    'version': '18.0.1.0.0',
    'category': 'Manufacturing/Manufacturing',
    'summary': 'Add custom BOM Name field to Bill of Materials in Odoo 18',
    'author': 'Primesoft Technologies',
    'depends': ['mrp'],
    'data': [
        'views/mrp_bom_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}