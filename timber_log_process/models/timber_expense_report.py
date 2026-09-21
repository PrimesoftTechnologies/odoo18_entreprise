from odoo import models, api

class ReportTimberExpenseSummary(models.AbstractModel):
    _name = 'report.timber_log_process.report_timber_expense_template'
    _description = 'Timber Expense Summary Report Parser'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data:
            data = {}

        target_type = data.get('target_type')
        log_id = data.get('log_id')
        date_from = data.get('date_from')
        date_to = data.get('date_to')

        domain = []
        # Kama imechaguliwa log maalum
        if target_type == 'specific' and log_id:
            domain.append(('id', '=', int(log_id)))

        # Kuchuja kwa tarehe ya kupokelewa kwa gogo
        if date_from:
            domain.append(('date_received', '>=', date_from))
        if date_to:
            domain.append(('date_received', '<=', date_to))

        # Tunatafuta moja kwa moja kwenye timber.log ambapo gharama zipo
        logs = self.env['timber.log'].search(domain)
        
        # Tunajumlisha gharama zote za uendeshaji (total_expense) kutoka kwenye magogo yaliyopatikana
        total_amount = sum(logs.mapped('total_expense'))

        return {
            'doc_ids': docids,
            'doc_model': 'timber.expense.report.wizard',
            'data': data,
            'expenses': logs,  # Tunapitisha magogo kama orodha ya kuonesha kwenye ripoti
            'total_amount': total_amount,
            'currency_id': self.env.company.currency_id,
        }