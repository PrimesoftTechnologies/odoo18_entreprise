from odoo import models, fields

class ClearanceReportWizard(models.TransientModel):
    _inherit = 'clearance.report.wizard'

    # Tunatengeneza uwanja mpya wa sas_shipper kwa ajili ya kuchuja
    sas_shipper = fields.Many2one('res.partner', string='Shipper')

    def action_export_excel(self):
        # Unaweza kuongeza mantiki ya kuchuja data hapa kama inahitajika
        return super().action_export_excel()