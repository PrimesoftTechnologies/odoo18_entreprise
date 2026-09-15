{
    'name': 'Apex Sales Customizations',
    'version': '18.0.3.0.0',
    'category': 'Sales/Sales',
    'summary': 'Track quantity changes, delete reasons with wizard, and order revisions on sales orders and reports.',
    'depends': ['sale'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/sale_order_line_delete_wizard_views.xml',
        'reports/sale_report_templates.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}