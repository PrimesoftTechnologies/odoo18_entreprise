from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    external_logo_hill = fields.Image(
        string='External Company Logo',
        max_width=1024,
        max_height=1024,
        help="The logo that will be used outside the system (login page, password reset, and signup pages). "
             "Inside the system (reports and navbar), the main logo will continue to be used."
    )
