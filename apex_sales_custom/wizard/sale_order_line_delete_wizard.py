from odoo import models, fields

class SaleOrderLineDeleteWizard(models.TransientModel):
    _name = 'sale.order.line.delete.wizard'
    _description = 'Sale Order Line Delete Reason Wizard'

    sale_order_line_id = fields.Many2one('sale.order.line', string='Order Line', required=True)
    reason = fields.Text(string='Reason for Deletion', required=True)

    def action_confirm_delete(self):
        self.ensure_one()
        line = self.sale_order_line_id
        order = line.order_id
        product_name = line.product_id.name or "Unknown Product"
        
        message = (
            f"Product Removed: '{product_name}' (Qty: {line.product_uom_qty}). "
            f"Reason: {self.reason}"
        )
        order.message_post(body=message)
        
        return line.with_context(skip_delete_wizard=True).unlink()