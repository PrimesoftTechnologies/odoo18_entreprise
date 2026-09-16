{
    'name': 'SAS Logistics Shipper Filter',
    'version': '18.0.1.0.0',
    'category': 'Logistics',
    'summary': 'Adds sas_shipper filter to clearance report wizard',
    'author': 'SAS Logistics',
    'depends': ['base', 'sas'],
    'data': [
        'views/clearance_report_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}