{
    'name': 'Purchase Order Custom Approval',
    'version': '18.0.1.0.0',
    'category': 'Purchases',
    'summary': 'Multi-level approval for Purchase Orders (Procurement & Finance Manager)',
    'author': 'Primesoft Technologies',
    'sequence':-27,
    'depends': ['purchase'],
    'data': [
        'security/ir.model.access.csv',
        'wizards/purchase_order_reject_wizard_views.xml',
        'views/res_company_views.xml',
        'views/purchase_order_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}