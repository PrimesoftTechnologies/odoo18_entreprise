{
    'name': 'Timber Log Processing & Inventory',
    'version': '18.0.1.0.0',
    'category': 'Manufacturing/Inventory',
    'summary': 'Complete Timber Management: Logs, Measurements, Sawing/Processing, Boards, CBM Calculation, Stock Link & Traceability',
    'description': '''
        Custom Timber Management Module for Odoo 18.
        Features:
        - Logs Management with Automatic Log CBM Calculation from Circumference & Length.
        - Operational Expenses Tracking (Fuel, Transport, Food, Purchase Amount).
        - Sawing/Processing Orders with Input CBM, Output CBM, and Waste CBM tracking.
        - Timber Boards Management with individual dimensions (Width, Thickness, Length) and CBM.
        - Seamless Stock Link with Odoo Inventory (Warehouses, Transfers, Movements).
        - Comprehensive Reports: Professional PDF Log Report with Company Logo, Production Report, Traceability.
        - End-to-end traceability from Vendor Purchase to Customer Delivery.
    ''',
    'author': 'Custom Timber Solution',
    'depends': ['base', 'mail', 'stock', 'purchase', 'sale', 'uom'],
    'data': [
        'security/timber_security.xml',
        'security/ir.model.access.csv',
        'data/timber_sequence.xml',
        'views/timber_dashboard_views.xml',
        'views/timber_log_views.xml',
        'views/timber_processing_views.xml',
        'views/timber_board_views.xml',
        'views/timber_expense_wizard_views.xml',  
        'views/timber_report_views.xml',  
        'views/timber_menus.xml',
        'views/timber_config_settings_views.xml',
    ],
    'images': [
        'static/description/icon.png',
        'static/description/er.png',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}