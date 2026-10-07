from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ShippingOrder(models.Model):
    _inherit = 'shipping.order'

    bl_awb_number = fields.Char(required=True)
    supplier_invoice_no = fields.Char(required=True)
    client_po_number = fields.Char(required=True)

    _sql_constraints = [
        ('client_po_number_uniq', 'unique(client_po_number)', 'The Client PO No. must be unique! A record with this PO number already exists.')
    ]

    @api.onchange('client_po_number')
    def _onchange_client_po_number(self):
        if self.client_po_number:
            existing = self.env['shipping.order'].search([
                ('client_po_number', '=', self.client_po_number),
            ], limit=1)
            if existing:
                return {
                    'warning': {
                        'title': "Warning: Client PO No. Already Exists!",
                        'message': f"The Client PO No. '{self.client_po_number}' is already used in another shipping order. Please use a unique PO number."
                    }
                }

    def action_submit(self):
        for record in self:
            if record.client_po_number:
                existing = self.search([
                    ('client_po_number', '=', record.client_po_number),
                    ('id', '!=', record.id)
                ], limit=1)
                if existing:
                    raise ValidationError(f"Client PO No. '{record.client_po_number}' already exists in another Shipping Order! Please use a unique PO number.")
        return super(ShippingOrder, self).action_submit()