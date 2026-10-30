# -*- coding: utf-8 -*-
{
    'name': 'Login Show/Hide Password - PrimeSoft Tech',
    'version': '18.0.1.0.0',
    'category': 'Website/Login',
    'summary': 'Adds a show/hide (eye) icon on the password fields of the login, signup and reset password pages.',
    'description': """
Login Show/Hide Password
========================
Adds an eye icon inside the password field on the Odoo 18 login page
(also works on the signup and reset password pages) so users can
show or hide what they type.
    """,
    'author': 'PrimeSoft Tech',
    'website': 'https://primesoft.tech',
    'license': 'LGPL-3',
    'depends': ['web'],
    'data': [],
    'assets': {
        'web.assets_frontend': [
            'odoo_login_primesoft_tech/static/src/scss/login_password_toggle.scss',
            'odoo_login_primesoft_tech/static/src/js/login_password_toggle.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
