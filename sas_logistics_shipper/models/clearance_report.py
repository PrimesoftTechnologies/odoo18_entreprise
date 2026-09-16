from odoo import models, fields

class ShippingClearanceReport(models.TransientModel):
    _inherit = 'shipping.clearance.report'  # Badilisha kuwa model husika ya sas kama ni tofauti

    # Tunaongeza uwanja mpya wa Shipper
    sas_shipper = fields.Many2one('res.partner', string='Shipper')

    def action_export_xlsx(self):
        # Unaweza kuongeza mantiki ya kuchuja kwa kutumia self.sas_shipper hapa kama inahitajika
        return super().action_export_xlsx()