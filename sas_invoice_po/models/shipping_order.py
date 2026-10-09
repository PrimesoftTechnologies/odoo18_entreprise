from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ShippingOrder(models.Model):
    _inherit = 'shipping.order'

    bl_awb_number = fields.Char(required=True)
    supplier_invoice_no = fields.Char(required=True)
    client_po_number = fields.Char(required=True)
    
    # Many2many ir.attachment field for multiple files
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'shipping_order_ir_attachment_rel',
        'order_id',
        'attachment_id',
        string="Shipping Documents Attachments",
        required=True,
        help="Upload mandatory minimum 3 shipping documents here."
    )

    _sql_constraints = [
        ('client_po_number_uniq', 'unique(client_po_number)', 'The Client PO No. must be unique! A record with this PO number already exists.'),
        ('bl_awb_number_uniq', 'unique(bl_awb_number)', 'The B/L / AWB Number must be unique! A record with this number already exists.'),
        ('supplier_invoice_no_uniq', 'unique(supplier_invoice_no)', 'The Supplier Invoice No. must be unique! A record with this number already exists.')
    ]

    # Model constraint to ensure minimum 3 files are attached
    @api.constrains('attachment_ids')
    def _check_minimum_attachments(self):
        for record in self:
            if not record.attachment_ids or len(record.attachment_ids) < 3:
                raise ValidationError("Error: You must upload at least 3 attachment files (Minimum 3 attachments) before saving this Shipping Order!")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            lines = vals.get('line_ids', [])
            if not lines:
                raise ValidationError("You cannot save a Shipping Order without adding at least one cargo line.")
            
            has_product = False
            for command in lines:
                if len(command) >= 3 and command[2] and command[2].get('product_id'):
                    has_product = True
                    break
            if not has_product:
                raise ValidationError("Every cargo line must have a valid Product selected before you can save.")
            
            # Verify attachments count during creation
            att_ids = vals.get('attachment_ids', [])
            total_attachments = 0
            for cmd in att_ids:
                if isinstance(cmd, (list, tuple)) and len(cmd) >= 3 and cmd[0] == 6:
                    total_attachments += len(cmd[2])
                elif isinstance(cmd, (list, tuple)) and cmd[0] in (4, 1):
                    total_attachments += 1
            if total_attachments < 3:
                raise ValidationError("You must upload at least 3 attachment files (Minimum 3 attachments) before saving this Shipping Order!")
                
        records = super(ShippingOrder, self).create(vals_list)
        
        for record in records:
            if record.attachment_ids:
                record.attachment_ids.write({
                    'res_model': 'shipping.order',
                    'res_id': record.id,
                })
        return records

    def write(self, vals):
        for record in self:
            if 'line_ids' in vals:
                lines = vals.get('line_ids', [])
                if not lines and not record.line_ids:
                    raise ValidationError("You cannot save a Shipping Order without at least one cargo line.")
                
                has_product = False
                active_lines = record.line_ids
                if active_lines:
                    has_product = True
                
                for command in lines:
                    if command[0] in (0, 1) and command[2] and command[2].get('product_id'):
                        has_product = True
                
                if not has_product:
                    raise ValidationError("You must select a Product for all cargo lines before saving.")

        res = super(ShippingOrder, self).write(vals)
        
        for record in self:
            if record.attachment_ids:
                record.attachment_ids.filtered(lambda att: not att.res_id).write({
                    'res_model': 'shipping.order',
                    'res_id': record.id,
                })
            # Ensure attachments do not drop below 3 on modification
            if len(record.attachment_ids) < 3:
                raise ValidationError("You cannot reduce the attachments to fewer than 3. At least 3 documents are required!")

        return res

    @api.onchange('client_po_number', 'bl_awb_number', 'supplier_invoice_no')
    def _onchange_unique_references(self):
        if self.client_po_number:
            existing_po = self.env['shipping.order'].search([
                ('client_po_number', '=', self.client_po_number),
            ], limit=1)
            if existing_po:
                return {
                    'warning': {
                        'title': "Warning: Client PO No. Already Exists!",
                        'message': f"The Client PO No. '{self.client_po_number}' is already used in another shipping order."
                    }
                }
        
        if self.bl_awb_number:
            existing_bl = self.env['shipping.order'].search([
                ('bl_awb_number', '=', self.bl_awb_number),
            ], limit=1)
            if existing_bl:
                return {
                    'warning': {
                        'title': "Warning: B/L / AWB Number Already Exists!",
                        'message': f"The B/L / AWB Number '{self.bl_awb_number}' is already used in another shipping order."
                    }
                }

        if self.supplier_invoice_no:
            existing_inv = self.env['shipping.order'].search([
                ('supplier_invoice_no', '=', self.supplier_invoice_no),
            ], limit=1)
            if existing_inv:
                return {
                    'warning': {
                        'title': "Warning: Supplier Invoice No. Already Exists!",
                        'message': f"The Supplier Invoice No. '{self.supplier_invoice_no}' is already used in another shipping order."
                    }
                }

    def action_submit(self):
        for record in self:
            if not record.line_ids or any(not line.product_id for line in record.line_ids):
                raise ValidationError("You cannot submit a Shipping Order without selecting a Product for all cargo lines.")

            if not record.attachment_ids or len(record.attachment_ids) < 3:
                raise ValidationError("You cannot submit a Shipping Order without at least 3 attachment files (Minimum 3 attachments)!")

            if record.client_po_number:
                existing_po = self.search([
                    ('client_po_number', '=', record.client_po_number),
                    ('id', '!=', record.id)
                ], limit=1)
                if existing_po:
                    raise ValidationError(f"Client PO No. '{record.client_po_number}' already exists in another Shipping Order!")

            if record.bl_awb_number:
                existing_bl = self.search([
                    ('bl_awb_number', '=', record.bl_awb_number),
                    ('id', '!=', record.id)
                ], limit=1)
                if existing_bl:
                    raise ValidationError(f"B/L / AWB Number '{record.bl_awb_number}' already exists in another Shipping Order!")

            if record.supplier_invoice_no:
                existing_inv = self.search([
                    ('supplier_invoice_no', '=', record.supplier_invoice_no),
                    ('id', '!=', record.id)
                ], limit=1)
                if existing_inv:
                    raise ValidationError(f"Supplier Invoice No. '{record.supplier_invoice_no}' already exists in another Shipping Order!")

        return super(ShippingOrder, self).action_submit()