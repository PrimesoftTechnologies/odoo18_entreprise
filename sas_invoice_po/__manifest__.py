{
    'name': 'SAS Invoice PO Customizations',
    'version': '1.0',
    'category': 'Logistics',
    'summary': 'Customizations for B/L, Supplier Invoice, and Unique Client PO Number',
    'description': 'Custom module sas_invoice_po to make bl_awb_number, supplier_invoice_no, and client_po_number required, enforce unique client_po_number, and add search filter for PO No.',
    'depends': ['sas', 'account'],
    'data': [
        'views/shipping_order_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
