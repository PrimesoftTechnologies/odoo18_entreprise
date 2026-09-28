from odoo import models, fields, api, _

class EstateProject(models.Model):
    _name = 'estate.project'
    _description = 'Real Estate Project'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Project Name', required=True, tracking=True)
    code = fields.Char(string='Project Code', required=True, tracking=True)
    rera_reg_no = fields.Char(string='RERA Reg No', tracking=True)
    project_type = fields.Selection([
        ('residential', 'Residential'),
        ('commercial', 'Commercial'),
        ('mixed', 'Mixed Use'),
        ('redevelopment', 'Redevelopment')
    ], string='Project Type', default='residential', required=True, tracking=True)

    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', tracking=True)
    site_engineer_ids = fields.Many2many('res.users', 'estate_project_site_engineer_rel', 'project_id', 'user_id', string='Site Engineers')
    architect_id = fields.Many2one('res.partner', string='Architect', domain="[('is_company', '=', False)]")

    occupancy_certificate = fields.Binary(string='Occupancy Certificate (OC)', attachment=True)
    oc_filename = fields.Char(string='OC Filename')
    oc_date = fields.Date(string='OC Date', tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('sanctioned', 'Sanctioned'),
        ('construction', 'Under Construction'),
        ('handover', 'Handover Phase'),
        ('closed', 'Closed')
    ], string='Status', default='draft', required=True, tracking=True)

    building_ids = fields.One2many('estate.building', 'project_id', string='Buildings')
    building_count = fields.Integer(string='Building Count', compute='_compute_building_count')

    total_units_count = fields.Integer(string='Total Units', compute='_compute_project_stats')
    available_units_count = fields.Integer(string='Available Units', compute='_compute_project_stats')
    active_leases_count = fields.Integer(string='Active Leases', compute='_compute_project_stats')
    boq_count = fields.Integer(string='BOQ Count', compute='_compute_project_stats')
    feasibility_count = fields.Integer(string='Feasibility Studies', compute='_compute_project_stats')
    sanction_count = fields.Integer(string='Sanctions & Permits', compute='_compute_project_stats')

    @api.depends('building_ids')
    def _compute_building_count(self):
        for rec in self:
            rec.building_count = len(rec.building_ids)

    def _compute_project_stats(self):
        for rec in self:
            units = self.env['estate.unit'].search([('project_id', '=', rec.id)])
            rec.total_units_count = len(units)
            rec.available_units_count = len(units.filtered(lambda u: u.state == 'available'))
            rec.active_leases_count = self.env['estate.lease.contract'].search_count([('project_id', '=', rec.id), ('state', '=', 'active')])
            rec.boq_count = self.env['estate.boq'].search_count([('project_id', '=', rec.id)])
            rec.feasibility_count = self.env['estate.feasibility'].search_count([('project_id', '=', rec.id)])
            rec.sanction_count = self.env['estate.sanction'].search_count([('project_id', '=', rec.id)])

    def action_view_units(self):
        self.ensure_one()
        return {
            'name': _('Project Units'),
            'type': 'ir.actions.act_window',
            'res_model': 'estate.unit',
            'domain': [('project_id', '=', self.id)],
            'view_mode': 'kanban,list,form',
        }

    def action_view_boq(self):
        self.ensure_one()
        return {
            'name': _('Project BOQs'),
            'type': 'ir.actions.act_window',
            'res_model': 'estate.boq',
            'domain': [('project_id', '=', self.id)],
            'view_mode': 'list,form',
        }

    def action_view_sanctions(self):
        self.ensure_one()
        return {
            'name': _('Project Permits & Sanctions'),
            'type': 'ir.actions.act_window',
            'res_model': 'estate.sanction',
            'domain': [('project_id', '=', self.id)],
            'view_mode': 'list,form',
        }

    def action_view_leases(self):
        self.ensure_one()
        return {
            'name': _('Active Leases'),
            'type': 'ir.actions.act_window',
            'res_model': 'estate.lease.contract',
            'domain': [('project_id', '=', self.id)],
            'view_mode': 'list,form',
        }

    def action_set_sanctioned(self):
        self.write({'state': 'sanctioned'})

    def action_set_construction(self):
        self.write({'state': 'construction'})

    def action_set_handover(self):
        self.write({'state': 'handover'})

    def action_set_closed(self):
        self.write({'state': 'closed'})

