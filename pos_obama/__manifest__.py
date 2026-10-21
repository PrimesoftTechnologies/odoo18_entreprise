{
    'name': 'POS Obama - Show Product Reference',
    'version': '18.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Show Internal Reference (default_code) on POS product cards',
    'depends': ['point_of_sale'],
    'data': [],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_obama/static/src/app/product_card.js',
            'pos_obama/static/src/app/product_card.xml',
            'pos_obama/static/src/app/product_card.scss',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
