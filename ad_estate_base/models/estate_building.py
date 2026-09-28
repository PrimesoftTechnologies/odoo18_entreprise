from odoo import models, fields, api

class EstateBuilding(models.Model):
    _name = 'estate.building'
    _description = 'Real Estate Building / Block'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Building Name / Wing', required=True, tracking=True)
    code = fields.Char(string='Building / Wing Code', tracking=True)
    project_id = fields.Many2one('estate.project', string='Project', required=True, ondelete='cascade', tracking=True)
    total_floors = fields.Integer(string='Total Floors', default=1)
    unit_ids = fields.One2many('estate.unit', 'building_id', string='Units')
    unit_count = fields.Integer(string='Unit Count', compute='_compute_unit_count')

    @api.depends('unit_ids')
    def _compute_unit_count(self):
        for rec in self:
            rec.unit_count = len(rec.unit_ids)
