{
    'name': 'Batch Generate Invoice',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'sequence': -26,
    'summary': 'Generate batch invoice reports with SAS Reference and Antrak Job No',
    'author': 'Primesoft Technologies',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'views/wizard_views.xml',
        'views/server_action.xml',
        'reports/batch_report.xml', 
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}