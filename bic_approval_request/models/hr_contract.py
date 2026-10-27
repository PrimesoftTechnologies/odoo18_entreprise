from odoo import fields, models


class HrContract(models.Model):
    _inherit = 'hr.contract'

    tuico = fields.Boolean("TUICO", default=False)
