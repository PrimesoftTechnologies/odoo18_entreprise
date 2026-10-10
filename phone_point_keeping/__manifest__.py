{
    'name': 'Phone Point Keeping (Mobile Shop Management with IMEI Tracking & Profit Calculation)',

    'version': '18.0.1.0.0',

    'category': 'Sales/Point of Sale',

    'summary': 'Advanced Phone Shop Management with IMEI Tracking, Profit Calculation & Custom Dashboard',

    'author': 'TechLink Tanzania',

    'depends': [
        'base',
        'web',
        'mail',
        'hr',
        'contacts',
    ],

    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/menu.xml',
        'views/phone_stock_views.xml',
        'views/phone_trade_in_views.xml',
        'views/phone_purchase_order_views.xml',
        'report/phone_purchase_report.xml',
    ],

    'assets': {
        'web.assets_backend': [
            'phone_point_keeping/static/src/css/dashboard.css',
            'phone_point_keeping/static/src/js/dashboard_v2.js',
            'phone_point_keeping/static/src/xml/dashboard_template.xml',
            'phone_point_keeping/static/src/xml/components/*.xml',
        ],
    },

    'images': ['static/description/icon.png'],

    'installable': True,

    'application': True,

    'license': 'LGPL-3',
}