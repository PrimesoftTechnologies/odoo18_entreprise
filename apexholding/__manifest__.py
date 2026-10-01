# -*- coding: utf-8 -*-
{
    'name': "apexholding",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "Primesoft Technologies Limited",
    'website': "https://www.primesoft.co.tz",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','account','sale','stock','purchase'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        # 'views/res_config_settings.xml',
        'reports/delivery.xml',
        'reports/invoice.xml',
        'reports/sales.xml',
        'reports/purchase.xml',
        'reports/headerfooter.xml',
        #'views/views.xml',

    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}

