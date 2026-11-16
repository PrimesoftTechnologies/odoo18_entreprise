{
    'name': 'Apex Purchase Level Process',
    'version': '18.0.1.0.5',
    'category': 'Inventory/Purchase',
    'summary': 'Collected Order and In-Transit levels on purchase orders',
    'depends': ['purchase', 'purchase_stock'],
    'data': [
        'views/purchase_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
