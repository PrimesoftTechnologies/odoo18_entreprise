from odoo import api, models


class StockReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    @api.model
    def default_get(self, fields_list):
        # Runs when the Return button is clicked and the wizard opens
        ctx = self.env.context
        if ctx.get('active_model') == 'stock.picking' and ctx.get('active_id'):
            self.env['stock.picking'].browse(ctx['active_id'])._check_signed_delivery_slip_attached()
        return super().default_get(fields_list)

    def action_create_returns(self):
        self.picking_id._check_signed_delivery_slip_attached()
        return super().action_create_returns()
