from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ShippingOrder(models.Model):
    _inherit = 'shipping.order'

    bl_awb_number = fields.Char(required=True)
    supplier_invoice_no = fields.Char(required=True)
    client_po_number = fields.Char(required=True)

    _sql_constraints = [
        (
            'client_po_number_uniq',
            'unique(client_po_number)',
            'The Client PO No. must be unique!'
        ),
        (
            'bl_awb_number_uniq',
            'unique(bl_awb_number)',
            'The B/L / AWB Number must be unique!'
        ),
        (
            'supplier_invoice_no_uniq',
            'unique(supplier_invoice_no)',
            'The Supplier Invoice No. must be unique!'
        )
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            lines = vals.get('line_ids', [])

            if not lines:
                raise ValidationError(
                    "You cannot save a Shipping Order without adding at least one cargo line."
                )

            if not any(
                len(line) >= 3
                and line[2]
                and line[2].get('product_id')
                for line in lines
            ):
                raise ValidationError(
                    "Every cargo line must have a valid Product selected before you can save."
                )

        return super().create(vals_list)

    def write(self, vals):
        for record in self:
            if 'line_ids' in vals:
                lines = vals.get('line_ids', [])

                if not lines and not record.line_ids:
                    raise ValidationError(
                        "You cannot save a Shipping Order without adding at least one cargo line."
                    )

        return super().write(vals)

    @api.onchange(
        'client_po_number',
        'bl_awb_number',
        'supplier_invoice_no'
    )
    def _onchange_unique_references(self):
        if self.client_po_number:
            existing = self.search([
                ('client_po_number', '=', self.client_po_number),
                ('id', '!=', self._origin.id)
            ], limit=1)

            if existing:
                return {
                    'warning': {
                        'title': 'Client PO No. Already Exists!',
                        'message': (
                            f"Client PO No. '{self.client_po_number}' "
                            f"is already used."
                        )
                    }
                }

        if self.bl_awb_number:
            existing = self.search([
                ('bl_awb_number', '=', self.bl_awb_number),
                ('id', '!=', self._origin.id)
            ], limit=1)

            if existing:
                return {
                    'warning': {
                        'title': 'B/L / AWB Number Already Exists!',
                        'message': (
                            f"B/L / AWB Number '{self.bl_awb_number}' "
                            f"is already used."
                        )
                    }
                }

        if self.supplier_invoice_no:
            existing = self.search([
                ('supplier_invoice_no', '=', self.supplier_invoice_no),
                ('id', '!=', self._origin.id)
            ], limit=1)

            if existing:
                return {
                    'warning': {
                        'title': 'Supplier Invoice No. Already Exists!',
                        'message': (
                            f"Supplier Invoice No. "
                            f"'{self.supplier_invoice_no}' is already used."
                        )
                    }
                }

    def action_submit(self):
        for record in self:
            if (
                not record.line_ids
                or any(not line.product_id for line in record.line_ids)
            ):
                raise ValidationError(
                    "You cannot submit a Shipping Order without "
                    "selecting a Product for all cargo lines."
                )

            attachment_count = self.env['ir.attachment'].search_count([
                ('res_model', '=', 'shipping.order'),
                ('res_id', '=', record.id),
            ])

            if attachment_count == 0:
                raise ValidationError(
                    "You must upload at least one attachment "
                    "before submitting this Shipping Order!"
                )

        return super().action_submit()