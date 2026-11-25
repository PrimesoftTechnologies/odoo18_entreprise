{
    'name': 'Hill Location Owner',
    'version': '18.0.1.1.0',
    'category': 'Inventory/Inventory',
    'summary': 'Assign one or more owners to each stock location and require owner approval on internal transfers',
    'description': """
Hill Location Owner
===================
* Adds "Location Owners" (one or many internal users) on every stock location.
* Internal transfers: the source location owner validates first (-> Pending Validation),
  then ANY destination location owner validates or rejects.
""",
    'author': 'Hill',
    'license': 'LGPL-3',
    'depends': ['stock', 'mail'],
    'data': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
