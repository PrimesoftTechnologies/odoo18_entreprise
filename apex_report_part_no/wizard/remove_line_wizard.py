from odoo import fields, models


class ApexQuotationRemoveLine(models.TransientModel):
    _name = 'apex.quotation.remove.line'
    _description = 'Remove Quotation Product (Reason for LOST)'

    line_id = fields.Many2one('sale.order.line', required=True, ondelete='cascade')
    product_name = fields.Char(related='line_id.product_id.name', string='Product')
    reason_lost = fields.Text(string='Reason for LOST', required=True)

    def action_confirm(self):
        self.ensure_one()
        self.line_id.with_context(apex_lost_reason=self.reason_lost).unlink()
        return {'type': 'ir.actions.client', 'tag': 'soft_reload'}
