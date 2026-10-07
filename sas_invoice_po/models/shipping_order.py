from odoo import models, fields, api

class ShippingOrder(models.Model):
    _inherit = 'shipping.order'

    bl_awb_number = fields.Char(required=True)
    supplier_invoice_no = fields.Char(required=True)
    client_po_number = fields.Char(required=True)

    _sql_constraints = [
        ('client_po_number_uniq', 'unique(client_po_number)', 'The Client PO No. must be unique! A record with this PO number already exists.')
    ]
