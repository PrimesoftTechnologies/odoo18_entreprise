from odoo import models, fields, api, _

class EstateDashboard(models.Model):
    _name = 'estate.dashboard'
    _description = 'Real Estate Executive Command Center Dashboard'

    name = fields.Char(string='Dashboard Name', default='Real Estate Operational Dashboard')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    total_projects = fields.Integer(string='Total Projects', compute='_compute_base_metrics')
    active_projects = fields.Integer(string='Under Construction Projects', compute='_compute_base_metrics')
    total_buildings = fields.Integer(string='Total Buildings / Wings', compute='_compute_base_metrics')
    total_units = fields.Integer(string='Total Units', compute='_compute_base_metrics')
    available_units = fields.Integer(string='Available Units', compute='_compute_base_metrics')
    reserved_units = fields.Integer(string='Reserved Units', compute='_compute_base_metrics')
    sold_units = fields.Integer(string='Sold Units', compute='_compute_base_metrics')
    leased_units = fields.Integer(string='Leased Units', compute='_compute_base_metrics')

    @api.depends_context('uid')
    def _compute_base_metrics(self):
        for dash in self:
            dash.total_projects = self.env['estate.project'].search_count([])
            dash.active_projects = self.env['estate.project'].search_count([('state', '=', 'construction')])
            dash.total_buildings = self.env['estate.building'].search_count([])
            
            units = self.env['estate.unit'].search([])
            dash.total_units = len(units)
            dash.available_units = len(units.filtered(lambda u: u.state == 'available'))
            dash.reserved_units = len(units.filtered(lambda u: u.state == 'reserved'))
            dash.sold_units = len(units.filtered(lambda u: u.state == 'sold'))
            dash.leased_units = len(units.filtered(lambda u: u.state == 'leased'))

    def action_view_projects(self):
        return {
            'name': _('Projects'),
            'type': 'ir.actions.act_window',
            'res_model': 'estate.project',
            'view_mode': 'kanban,list,form',
        }

    def action_view_available_units(self):
        return {
            'name': _('Available Units'),
            'type': 'ir.actions.act_window',
            'res_model': 'estate.unit',
            'domain': [('state', '=', 'available')],
            'view_mode': 'kanban,list,form',
        }

    @api.model
    def get_owl_dashboard_data(self):
        total_projects = self.env['estate.project'].search_count([])
        active_projects = self.env['estate.project'].search_count([('state', '=', 'construction')])
        total_buildings = self.env['estate.building'].search_count([])
        
        units = self.env['estate.unit'].search([])
        total_units = len(units)
        available_units = len(units.filtered(lambda u: u.state == 'available'))
        reserved_units = len(units.filtered(lambda u: u.state == 'reserved'))
        sold_units = len(units.filtered(lambda u: u.state == 'sold'))
        leased_units = len(units.filtered(lambda u: u.state == 'leased'))

        # Sales metrics (safe check if module installed)
        sales_revenue = 0.0
        active_contracts = 0
        total_offers = 0
        if 'estate.sale.contract' in self.env:
            contracts = self.env['estate.sale.contract'].search([('state', 'in', ['active', 'completed'])])
            active_contracts = len(contracts)
            sales_revenue = sum(contracts.mapped('agreed_sale_price'))
        if 'estate.offer' in self.env:
            total_offers = self.env['estate.offer'].search_count([])

        # Tenancy metrics
        monthly_rent_roll = 0.0
        pending_maintenance = 0
        if 'estate.lease.contract' in self.env:
            active_leases = self.env['estate.lease.contract'].search([('state', '=', 'active')])
            monthly_rent_roll = sum(active_leases.mapped('monthly_rent')) + sum(active_leases.mapped('utility_cam_charge'))
        if 'maintenance.request' in self.env:
            pending_maintenance = self.env['maintenance.request'].search_count([('stage_id.done', '=', False)])

        # Recent Projects
        recent_projects = []
        for p in self.env['estate.project'].search([], limit=5, order='id desc'):
            recent_projects.append({
                'id': p.id,
                'name': p.name,
                'code': p.code,
                'project_type': p.project_type,
                'state': p.state,
                'building_count': p.building_count,
            })

        # Advanced chart breakdown datasets
        project_stage_data = {
            'draft': self.env['estate.project'].search_count([('state', '=', 'draft')]),
            'sanctioned': self.env['estate.project'].search_count([('state', '=', 'sanctioned')]),
            'construction': active_projects,
            'handover': self.env['estate.project'].search_count([('state', '=', 'handover')]),
            'closed': self.env['estate.project'].search_count([('state', '=', 'closed')]),
        }

        # Unit Type Breakdown
        unit_types = self.env['estate.unit.type'].search([])
        unit_type_breakdown = []
        for ut in unit_types:
            count = len(units.filtered(lambda u: u.unit_type_id.id == ut.id))
            if count > 0:
                unit_type_breakdown.append({
                    'name': ut.name,
                    'count': count,
                })

        # Recent Transactions (Sale Contracts + Lease Contracts)
        recent_transactions = []
        if 'estate.sale.contract' in self.env:
            for sc in self.env['estate.sale.contract'].search([], limit=5, order='id desc'):
                recent_transactions.append({
                    'ref': sc.name,
                    'type': 'Sale Agreement',
                    'partner': sc.partner_id.name,
                    'unit': sc.unit_id.name,
                    'amount': sc.agreed_sale_price,
                    'state': sc.state,
                })
        if 'estate.lease.contract' in self.env:
            for lc in self.env['estate.lease.contract'].search([], limit=5, order='id desc'):
                recent_transactions.append({
                    'ref': lc.name,
                    'type': 'Tenancy Lease',
                    'partner': lc.tenant_id.name,
                    'unit': lc.unit_id.name,
                    'amount': lc.monthly_rent,
                    'state': lc.state,
                })

        return {
            'total_projects': total_projects,
            'active_projects': active_projects,
            'total_buildings': total_buildings,
            'total_units': total_units,
            'available_units': available_units,
            'reserved_units': reserved_units,
            'sold_units': sold_units,
            'leased_units': leased_units,
            'sales_revenue': sales_revenue,
            'active_contracts': active_contracts,
            'total_offers': total_offers,
            'monthly_rent_roll': monthly_rent_roll,
            'pending_maintenance': pending_maintenance,
            'recent_projects': recent_projects,
            'project_stage_data': project_stage_data,
            'unit_type_breakdown': unit_type_breakdown,
            'recent_transactions': recent_transactions,
        }


