{
    'name': 'BIC Approval Request',
    'version': '18.0.1.0.0',
    'summary': 'Two-level Purchase Order approval (Finance & CEO) with signature blocks on PO, Delivery, and Invoice reports',
    'category': 'Inventory/Purchase',
    'author': 'BIC',
    'depends': ['purchase', 'account'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/purchase_order_views.xml',
        'report/purchase_order_report.xml',
        'report/delivery_slip_report.xml',
        'report/invoice_report.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}