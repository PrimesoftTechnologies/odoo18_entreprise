{
    'name': 'Hill Location Owner',
    'version': '18.0.1.5.0',
    'category': 'Inventory/Inventory',
    'summary': 'Assign one or more owners to each stock location and require owner approval on internal transfers, receipts, deliveries and pick components',
    'description': """
Hill Location Owner
===================
* Adds "Location Owners" (one or many internal users) on every stock location.
* Internal transfers, receipts, deliveries and pick components: a starter validates first
  (-> Pending Validation), then ANY approving location owner validates or rejects
  (destination owners for internal/receipt/pick components, source owners for delivery).
""",
    'author': 'Hill',
    'license': 'LGPL-3',
    'depends': ['stock', 'mail', 'bus'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'hill_location_owner/static/src/js/approval_bell.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
