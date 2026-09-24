{
    'name': 'Engineering Site Survey',
    'version': '18.0.3.0.0',
    'summary': 'Plan engineering site surveys, accommodation, payment requests and survey reports',
    'category': 'Services/Project',
    'author': 'Primesoft Technologies Limited',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'contacts', 'hr', 'project', 'crm', 'helpdesk'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'data/expense_type_data.xml',
        'views/engineering_site_survey_views.xml',
        'views/engineering_site_survey_wizard_views.xml',
        'report/site_survey_report.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'engineering_site_survey/static/src/xml/dashboard_template.xml',
            'engineering_site_survey/static/src/js/dashboard.js',
        ],
    },
    'images': ['static/description/icon.png'],
    'application': True,
    'installable': True,
}