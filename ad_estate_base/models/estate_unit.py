from odoo import models, fields, api, _

class EstateUnitAmenity(models.Model):
    _name = 'estate.unit.amenity'
    _description = 'Unit Amenity'

    name = fields.Char(string='Amenity Name', required=True)
    code = fields.Char(string='Code')

class EstateUnitType(models.Model):
    _name = 'estate.unit.type'
    _description = 'Estate Unit Type'

    name = fields.Char(string='Unit Type Name', required=True) # e.g., 2BHK, 3BHK, Penthouse, Retail Shop
    code = fields.Char(string='Code')

class EstateUnit(models.Model):
    _name = 'estate.unit'
    _description = 'Real Estate Unit / Property'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Unit Name / No.', required=True, tracking=True)
    project_id = fields.Many2one('estate.project', string='Project', required=True, tracking=True)
    building_id = fields.Many2one('estate.building', string='Building / Wing', domain="[('project_id', '=', project_id)]", tracking=True)
    unit_type_id = fields.Many2one('estate.unit.type', string='Unit Type', required=True)

    carpet_area = fields.Float(string='Carpet Area (sq ft)', required=True, tracking=True)
    builtup_area = fields.Float(string='Built-up Area (sq ft)')
    super_builtup_area = fields.Float(string='Super Built-up Area (sq ft)')
    fsi_area = fields.Float(string='FSI Area (sq ft)')
    floor = fields.Integer(string='Floor Number', default=0)
    facing = fields.Selection([
        ('north', 'North'),
        ('south', 'South'),
        ('east', 'East'),
        ('west', 'West'),
        ('north_east', 'North-East'),
        ('north_west', 'North-West'),
        ('south_east', 'South-East'),
        ('south_west', 'South-West')
    ], string='Facing Direction', default='east')

    pricing_mode = fields.Selection([
        ('sale', 'Sale'),
        ('lease', 'Lease'),
        ('both', 'Both Sale & Lease')
    ], string='Pricing Mode', default='sale', required=True)

    base_price = fields.Monetary(string='Base Sale Price', currency_field='currency_id', tracking=True)
    security_deposit_amount = fields.Monetary(string='Security Deposit', currency_field='currency_id', tracking=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    state = fields.Selection([
        ('available', 'Available'),
        ('reserved', 'Reserved'),
        ('sold', 'Sold'),
        ('leased', 'Leased'),
        ('handover_pending', 'Handover Pending')
    ], string='Status', default='available', required=True, tracking=True)

    current_owner_id = fields.Many2one('res.partner', string='Current Owner', domain="[('is_buyer', '=', True)]", tracking=True)
    current_tenant_id = fields.Many2one('res.partner', string='Current Tenant', domain="[('is_tenant', '=', True)]", tracking=True)
    amenity_ids = fields.Many2many('estate.unit.amenity', string='Amenities')
