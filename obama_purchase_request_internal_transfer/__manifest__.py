{
    'name': 'Purchase Request - Internal Transfer',
    'version': '18.0.3.0.0',
    'category': 'Inventory/Purchase',
    'summary': 'Hide Create RFQ and show Internal Transfer button when the Picking Type is Internal Transfer',
    'author': 'Obama',
    'license': 'LGPL-3',
    # BADILISHA 'purchase_request' kuwa technical name ya module yako ya Purchase Requests
    'depends': ['product', 'mail', 'stock', 'purchase', 'purchase_request'],
    'data': [],
    'installable': True,
    'application': False,
}
