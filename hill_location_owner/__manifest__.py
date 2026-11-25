{
    'name': 'Hill Location Owner',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Assign an owner to each stock location and require owner approval on internal transfers',
    'description': """
Hill Location Owner
===================
* Adds a "Location Owner" (internal user) on every stock location.
* Internal transfers: the source location owner validates first (-> Pending Validation),
  then the destination location owner validates or rejects.
""",
    'author': 'Hill',
    'license': 'LGPL-3',
    'depends': ['stock', 'mail'],
    'data': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
