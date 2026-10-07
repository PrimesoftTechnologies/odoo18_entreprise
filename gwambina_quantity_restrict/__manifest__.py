# -*- coding: utf-8 -*-
{
    'name': 'Gwambina Quantity Restrict',
    'version': '18.0.1.0.0',
    'category': 'Purchases',
    'summary': 'Restrict editing product quantity after submitting Purchase Order for approval',
    'author': 'Gwambina Group',
    'depends': ['purchase'],
    'data': [
        'views/purchase_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}