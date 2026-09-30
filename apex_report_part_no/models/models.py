from odoo import models, fields

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    delivery_details = fields.Char(string="Delivery Details")
    delivery_terms = fields.Char(string="Delivery Terms")
    grn_no = fields.Char(string="GRN No.")

class StockMove(models.Model):
    _inherit = 'stock.move'

    x_remark = fields.Char(string="Remarks")