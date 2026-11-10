from odoo import _, models
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _check_tin_required(self):
        missing = self.filtered(lambda p: not (p.vat or '').strip())
        if missing:
            raise UserError(_(
                "TIN Number is mandatory for customers and vendors. "
                "Please fill the TIN Number on: %s",
                ', '.join(missing.mapped('display_name')),
            ))
