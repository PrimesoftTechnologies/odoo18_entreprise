{
    'name': 'External Logo Hill',
    'version': '18.0.1.0.0',
    'category': 'Hidden/Tools',
    'summary': 'Tumia External Logo kwenye login page (ukiwa logout), main logo ibaki ndani ya system',
    'description': """
Inaongeza field ya "External Logo" kwenye Company (Settings > Companies).
- Ukiwa logged out (login, reset password, signup) -> External Logo inaonekana.
- Ukiwa ndani ya system (reports, navbar, documents) -> Main logo inaendelea kutumika.
- Kama External Logo haijajazwa, system inatumia main logo kama kawaida.
    """,
    'author': 'Hill',
    'license': 'LGPL-3',
    'depends': ['base', 'web'],
    'data': [
        'views/res_company_views.xml',
        'views/login_templates.xml',
    ],
    'installable': True,
    'application': False,
}
