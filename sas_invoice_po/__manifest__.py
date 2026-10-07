{
    'name': 'SAS Invoice PO Customizations',
    'version': '1.0',
    'category': 'Accounting/Logistics',
    'summary': 'Customizations for B/L, Supplier Invoice, Unique Client PO Number, and PO No Invoice Search',
    'description': 'Custom module sas_invoice_po to make bl_awb_number, supplier_invoice_no, and client_po_number required, enforce unique client_po_number via python and sql constraint, and add search/group filter for account.move po_no.',
    'depends': ['sas', 'account'],
    'data': [
        'views/invoice_search_views.xml',
        'views/clearance_record_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
