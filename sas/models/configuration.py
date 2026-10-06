from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval

class FreightPort(models.Model):
    """Model for Freight Ports"""
    _name = 'freight.port'
    _description = 'Freight Port'

    name = fields.Char(string='Port Name', required=True)
    country_id = fields.Many2one('res.country', string='Country', required=True)
    code = fields.Char(string='Port Code', required=True)
    type = fields.Selection([('sea', 'Sea'), ('air', 'Air'), ('land', 'Land')], string='Port Type')