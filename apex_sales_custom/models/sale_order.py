from odoo import models, api, _

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def write(self, vals):
        if 'product_uom_qty' in vals:
            for line in self:
                old_qty = line.product_uom_qty
                new_qty = vals['product_uom_qty']
                if old_qty != new_qty:
                    product_name = line.product_id.name or "Unknown Product"
                    message = (
                        f"Quantity changed for product '{product_name}': "
                        f"from {old_qty} to {new_qty}"
                    )
                    line.order_id.message_post(body=message)
        return super(SaleOrderLine, self).write(vals)

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