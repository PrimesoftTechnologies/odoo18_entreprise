{
    'name': 'Analytic Account on Delivery Valuation',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Accounting',
    'summary': 'Adds Analytic Account to Delivery Orders and stock valuation moves',
    'depends': ['stock', 'account', 'analytic'],
    'data': [
        'views/stock_picking_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
