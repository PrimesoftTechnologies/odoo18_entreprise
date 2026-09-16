{
    'name': 'SAS Logistics Shipper Filter',
    'version': '16.0.1.0.0',
    'category': 'Logistics',
    'summary': 'Adds sas_shipper filter to clearance report wizard',
    'depends': ['base', 'sas'], # Badilisha iendane na jina la moduli yako ya sasa
    'data': [
        'views/clearance_report_views.xml',
    ],
    'installable': True,
    'auto_install': False,
}