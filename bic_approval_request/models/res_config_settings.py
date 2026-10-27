from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_tuico_visible = fields.Boolean(
        string="TUICO",
        implied_group='bic_approval_request.group_tuico_visible',
        help="Show the TUICO field on employee contracts.",
    )
