{
    'name': 'Report Source and Destination Location',
    'version': '18.0.1.0.0',
    'sequence': -32,
    'category': 'Inventory/Inventory',
    'summary': 'Adds Source and Destination Locations to Delivery Slip report',
    'author': 'Primesoft Technologies',
    'depends': ['stock'],
    'data': [
        'views/report_deliveryslip.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}