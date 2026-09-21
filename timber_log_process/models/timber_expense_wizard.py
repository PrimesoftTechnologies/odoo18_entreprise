from odoo import models, fields, api

class TimberExpenseReportWizard(models.TransientModel):
    _name = 'timber.expense.report.wizard'
    _description = 'Timber Expense Report Wizard'

    target_type = fields.Selection([
        ('all', 'All Expenses (General Summary)'),
        ('specific', 'Specific Log Expenses')
    ], string='Report Scope', default='all', required=True)

    log_id = fields.Many2one('timber.log', string='Log Number')
    date_from = fields.Date(string='Start Date')
    date_to = fields.Date(string='End Date')

    def action_print_report(self):
        self.ensure_one()
        data = {
            'target_type': self.target_type,
            'log_id': self.log_id.id if self.log_id else False,
            'date_from': self.date_from.strftime('%Y-%m-%d') if self.date_from else False,
            'date_to': self.date_to.strftime('%Y-%m-%d') if self.date_to else False,
        }
        return self.env.ref('timber_log_process.action_report_timber_expense').report_action(self, data=data)