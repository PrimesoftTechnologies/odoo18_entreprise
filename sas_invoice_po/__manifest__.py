{
    'name': 'SAS Invoice PO Customizations',
    'version': '1.0',
    'category': 'Accounting/Logistics',
    'summary': 'Customizations for B/L, Supplier Invoice, Unique Client PO Number, PO No Invoice Search, and Security Access Views',
    'description': 'Custom module sas_invoice_po to make bl_awb_number, supplier_invoice_no, and client_po_number required, enforce unique client_po_number via python and sql constraint, add search/group filter for account.move po_no, and secure clearance record action and smart buttons for Bookkeepers and Administrators.',
    'depends': [
        'sas',
        'account',
        'mail',
        'web',
    ],
    'data': [
        'views/clearance_record_views.xml',
        'views/invoice_search_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'sas_invoice_po/static/src/js/shipping_order_attachment.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}