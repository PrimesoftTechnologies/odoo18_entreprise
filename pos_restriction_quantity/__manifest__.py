{
    'name': 'POS Restriction Quantity & Discount Limit',
    'version': '18.0.1.2.0',
    'category': 'Point of Sale',
    'summary': 'Block zero-stock sales and enforce a minimum selling price (discount limit) in POS',
    'description': """
POS Restriction Quantity & Discount Limit
=========================================
1. Storable products with On Hand = 0 (or not enough stock) can not be added to the POS order.
2. New field "Limit Discount" on the Product form (next to Sales Price). It is the lowest
   price the cashier may sell the product for. Example: Sales Price 80,000 and Limit Discount
   75,000 -> the cashier can sell at 75,000 or above, anything lower (74,999 and below) is refused.
   Applies to manual price changes and discounts in POS. 0 = no limit.
3. The numpad discount button (%) becomes "Disc. Price": the cashier types the ACTUAL selling
   price per unit (e.g. 70,000 or 60,000) instead of a percentage. The original price and the
   discount stay visible on the line.
    """,
    'depends': ['point_of_sale', 'stock'],
    'data': [
        'views/product_template_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_restriction_quantity/static/src/**/*',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
