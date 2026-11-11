from odoo import models

class PosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_product_product(self):
        result = super()._loader_params_product_product()
        if 'qty_available' not in result['search_params']['fields']:
            result['search_params']['fields'].append('qty_available')
        return result
