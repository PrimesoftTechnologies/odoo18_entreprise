from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_non_resident_visible = fields.Boolean(
        string="Non-Resident",
        implied_group='oscon_payroll.group_non_resident_visible',
        help="Show the Non-Resident field on employee contracts.",
    )
