{
    'name': 'Timber Industry (Native Odoo Integration)',
    'version': '18.0.2.0.2',
    'category': 'Manufacturing/Inventory',
    'summary': 'Timber logs, sawing and boards built on standard Odoo Purchase, Inventory, Manufacturing, Landed Costs and Sales',
    'description': """
Timber Industry on top of standard Odoo
=========================================
This module does NOT re-implement Odoo features. It configures and extends them:

* Purchasing logs ............ standard Purchase Order + Receipt
* Log stock .................. standard Inventory, each log = a Lot (unit m3)
* Sawing / production ........ standard Manufacturing Order + Bill of Materials
                               (finished boards + waste as a By-Product)
* Board / waste percentage ... Bill of Materials quantities (no custom settings)
* Expenses (fuel, transport,
  food, other) ............... standard Landed Costs
* Sales ...................... standard Sales Order + Delivery
* Reports .................... standard pivot / graph views + 2 PDF reports

Custom code is limited to: CBM measurement lines (circumference/length and
width/thickness/length), Transit Pass (TP) fields on the Receipt and a few
helper fields on Lots and Manufacturing Orders.
    """,
    'author': 'Custom Timber Solution',
    'license': 'LGPL-3',
    'depends': [
        'base', 'mail', 'uom',
        'stock', 'purchase', 'purchase_stock',
        'sale_management', 'sale_stock',
        'mrp', 'stock_landed_costs',
    ],
    'data': [
        'security/timber_security.xml',
        'security/ir.model.access.csv',
        'data/timber_data.xml',
        'views/product_views.xml',
        'views/stock_lot_views.xml',
        'views/stock_picking_views.xml',
        'views/mrp_production_views.xml',
        'views/timber_report_views.xml',
        'views/timber_dashboard_views.xml',
        'views/timber_menus.xml',
        'report/timber_report.xml',
    ],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
}
