from odoo import api, fields, models

class TimberDashboard(models.Model):
    _name = 'timber.dashboard'
    _description = 'Timber Dashboard Summary'

    name = fields.Char(string='Dashboard', default='Timber Operations Dashboard')
    
    # Vichujio vya Tarehe
    filter_from_date = fields.Date(string='From Date')
    filter_to_date = fields.Date(string='To Date')

    total_logs = fields.Integer(string='Total Logs', compute='_compute_dashboard_metrics')
    total_log_cbm = fields.Float(string='Total Log CBM', compute='_compute_dashboard_metrics', digits=(16, 4))
    total_sawing_orders = fields.Integer(string='Sawing Orders', compute='_compute_dashboard_metrics')
    total_board_cbm = fields.Float(string='Total Board CBM', compute='_compute_dashboard_metrics', digits=(16, 4))
    total_waste_cbm = fields.Float(string='Total Waste CBM', compute='_compute_dashboard_metrics', digits=(16, 4))
    
    # --- SEHEMU MPYA ZA GHARAMA KUTOKA KWENYE LOGS ---
    total_purchase_amount = fields.Float(string='Total Purchase Amount', compute='_compute_dashboard_metrics', digits=(16, 2))
    total_operational_expense = fields.Float(string='Total Operational Expenses', compute='_compute_dashboard_metrics', digits=(16, 2))
    grand_total_operations_cost = fields.Float(string='Grand Total Cost', compute='_compute_dashboard_metrics', digits=(16, 2))

    @api.depends('filter_from_date', 'filter_to_date')
    def _compute_dashboard_metrics(self):
        for rec in self:
            log_domain = []
            
            if rec.filter_from_date:
                log_domain.append(('date_received', '>=', rec.filter_from_date))
            if rec.filter_to_date:
                log_domain.append(('date_received', '<=', rec.filter_to_date))

            logs = self.env['timber.log'].search(log_domain)
            
            log_ids = logs.ids
            sawing = self.env['timber.processing'].search([('log_id', 'in', log_ids)] if log_ids else [])

            if not rec.filter_from_date and not rec.filter_to_date:
                logs = self.env['timber.log'].search([])
                sawing = self.env['timber.processing'].search([])

            rec.total_logs = len(logs)
            rec.total_log_cbm = sum(logs.mapped('total_cbm'))
            rec.total_sawing_orders = len(sawing)
            rec.total_board_cbm = sum(sawing.mapped('output_cbm'))
            rec.total_waste_cbm = sum(sawing.mapped('waste_cbm'))
            
            # Kuhesabu jumla za fedha kutoka kwenye magogo
            rec.total_purchase_amount = sum(logs.mapped('purchase_amount'))
            rec.total_operational_expense = sum(logs.mapped('total_expense'))
            rec.grand_total_operations_cost = sum(logs.mapped('grand_total_cost'))

    def action_apply_filter(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'timber.dashboard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
        }