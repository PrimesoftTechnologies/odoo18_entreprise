from odoo import models, fields

class MrpBoM(models.Model):
    _inherit = 'mrp.bom'

    bom_material_custom = fields.Char(string='BOM Name', tracking=True)