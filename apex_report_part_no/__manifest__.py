{
    'name': 'Apex Report Part No',
    'version': '18.0.2.0.0',
    'category': 'Sales/Purchase',
    'summary': 'Removes internal reference from sales and purchase quotation reports',
    'author': 'Apex',
    'depends': ['sale', 'purchase'],
    'data': [
        'views/sale_report_templates.xml',
        'views/purchase_report_templates.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}