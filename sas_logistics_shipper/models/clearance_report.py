from odoo import models, fields

class SasClearanceReportWizard(models.TransientModel):
    _inherit = 'sas.clearance.report.wizard'

    # Tunaongeza uwanja mpya wa Shipper kwenye wizard ya ripoti
    sas_shipper = fields.Many2one('res.partner', string='Shipper')

    def action_export_xlsx(self):
        # Unaweza kuongeza mantiki ya kuchuja data hapa kama inahitajika
        return super().action_export_xlsx()