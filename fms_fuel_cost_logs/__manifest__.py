{
    'name': 'FMS Fuel Cost Logs',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Fleet',
    'summary': 'Record fuel costs per vehicle from the Fleet menu',
    'depends': ['fleet', 'account', 'analytic', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/fuel_cost_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
