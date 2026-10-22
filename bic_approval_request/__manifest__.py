{
    'name': 'BIC Approval Request',
    'version': '18.0.1.0.0',
    'summary': 'Two-level Purchase Order approval (Finance & CEO) with signature block on PO report',
    'category': 'Inventory/Purchase',
    'author': 'BIC',
    'depends': ['purchase'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/purchase_order_views.xml',
        'report/purchase_order_report.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
