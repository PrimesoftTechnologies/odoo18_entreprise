{
    'name': 'POS Out of Stock Restriction',
    'version': '18.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Prevent selecting products in POS when On-Hand Quantity is 0 or less',
    'description': """
        This module restricts users from adding products to the POS order line 
        if the product's quantity on hand is zero or below zero.
    """,
    'author': 'Custom Development',
    'depends': ['point_of_sale'],
    'data': [],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_restriction/static/src/js/product_restriction.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
