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

    @api.constrains('client_po_number')
    def _check_client_po_number_unique(self):
        for record in self:
            if record.client_po_number:
                existing = self.search([
                    ('client_po_number', '=', record.client_po_number),
                    ('id', '!=', record.id)
                ], limit=1)
                if existing:
                    raise ValidationError(f"Client PO No. '{record.client_po_number}' already exists in another Shipping Order! Please use a unique PO number.")

    def action_submit(self):
        self._check_client_po_number_unique()
        return super(ShippingOrder, self).action_submit()
