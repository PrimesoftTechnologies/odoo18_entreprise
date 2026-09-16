from odoo import models, fields

class SasClearanceReportWizard(models.TransientModel):
    _inherit = 'sas.clearance.report.wizard'

    sas_shipper = fields.Many2one('res.partner', string='Shipper')

    def action_export_xlsx(self):
        # 1. Hakikisha domain inachuja kwa kutumia sas_shipper uliyochagua kwenye wizard
        domain = []
        if self.date_from:
            domain.append(('eta', '>=', self.date_from))
        if self.date_to:
            domain.append(('eta', '<=', self.date_to))
        if self.order_type:
            domain.append(('order_type', '=', self.order_type))
        if self.transport_mode:
            domain.append(('transport_mode', '=', self.transport_mode))
        if self.state:
            domain.append(('state', '=', self.state))
        if self.consignee_id:
            domain.append(('consignee_id', '=', self.consignee_id.id))
            
        # Hapa ndipo tunaunganisha uwanja wetu wa shipper kwenye uchujaji wa data za Excel
        if self.sas_shipper:
            domain.append(('shipper_id', '=', self.sas_shipper.id))

        # Unaweza kuendelea na code za asili za kutengeneza Excel kupitia super()
        res = super().action_export_xlsx()
        
        # Kama unatumia mfumo unaotengeneza data za Excel moja kwa moja hapa, 
        # hakikisha unaongeza column ya Shipper kwenye orodha ya mistari (lines) unayotuma kwenye Excel sheet.
        return res