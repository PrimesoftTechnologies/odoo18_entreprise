from odoo import models, fields, api

class ClearanceReportWizard(models.TransientModel):
    _inherit = 'clearance.report.wizard'  # Hakikisha hili ni jina sahihi la Model ya Wizard yako

    sas_shipper = fields.Many2one('res.partner', string='Shipper')

    def action_export_excel(self):
        # Kusanya domain/vichujio vilivyopo
        domain = []
        
        if hasattr(super(), 'action_export_excel'):
            # Kama kuna logic ya zamani, unaweza kuiita au kuweka domain yako hapa
            pass

        if self.sas_shipper:
            domain.append(('shipper_id', '=', self.sas_shipper.id))
            
        # Ongeza hapa mantiki yako ya kutafuta data na kutengeneza Excel
        return super().action_export_excel()