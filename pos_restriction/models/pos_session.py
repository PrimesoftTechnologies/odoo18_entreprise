from odoo import models

class PosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_product_product(self):
        result = super()._loader_params_product_product()
        # Ensure qty_available is loaded in POS product fields in Odoo 18
        if 'qty_available' not in result['search_params']['fields']:
            result['search_params']['fields'].append('qty_available')
        return result
