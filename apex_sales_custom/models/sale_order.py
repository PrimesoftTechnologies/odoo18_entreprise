from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    revision_number = fields.Integer(string='Revision Number', default=0, tracking=True)
    
    # Tunatengeneza field mpya ya kuonyesha namba yenye revision ambayo itajaza nafasi pale juu
    display_order_name = fields.Char(string='Order/Quotation Revision Name', compute='_compute_display_order_name', store=True)

    @api.depends('name', 'revision_number')
    def _compute_display_order_name(self):
        for order in self:
            name = order.name or 'New'
            if order.revision_number > 0 and name != 'New':
                order.display_order_name = f"{name}/REV-{order.revision_number:02d}"
            else:
                    order.display_order_name = name

    def _increment_revision(self, change_description="Order updated"):
        for order in self:
            if order.state in ['draft', 'sent'] and order.id:
                order.revision_number += 1
                rev_code = f"REV-{order.revision_number:02d}"
                order.message_post(body=f"Order revised to {rev_code}. Reason/Change: {change_description}")

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.model_create_multi
    def create(self, vals_list):
        lines = super(SaleOrderLine, self].create(vals_list) if hasattr(super(SaleOrderLine, self), 'create') else super().create(vals_list)
        for line in lines:
            if line.order_id and line.order_id.state in ['draft', 'sent']:
                product_name = line.product_id.name or "Product"
                line.order_id._increment_revision(f"Added product line: {product_name} (Qty: {line.product_uom_qty})")
        return lines

    def write(self, vals):
        res = super().write(vals)
        if 'product_uom_qty' in vals:
            for line in self:
                if line.order_id and line.order_id.state in ['draft', 'sent']:
                    product_name = line.product_id.name or "Product"
                    line.order_id._increment_revision(f"Updated quantity for '{product_name}' to {line.product_uom_qty}")
        return res

    def action_open_delete_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reason for Deletion',
            'res_model': 'sale.order.line.delete.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_sale_order_line_id': self.id},
        }