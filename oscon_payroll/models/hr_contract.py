from odoo import fields, models


class HrContract(models.Model):
    _inherit = 'hr.contract'

    non_resident = fields.Boolean("Non-Resident", default=False)
