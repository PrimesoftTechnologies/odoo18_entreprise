{
    'name': 'POS Restriction Quantity',
    'version': '18.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Block selling storable products with zero (or insufficient) on-hand quantity in POS',
    'description': """
POS Restriction Quantity
========================
While a POS session is open, a storable product whose on-hand quantity
(in the POS operation type's source location) is 0 can not be added to the order.
Also blocks adding more than the available quantity.
    """,
    'depends': ['point_of_sale', 'stock'],
    'data': [],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_restriction_quantity/static/src/**/*',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
