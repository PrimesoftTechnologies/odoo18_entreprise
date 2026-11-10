import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    car_id = fields.Many2one(
        'sale.car', string='Car Number',
        compute='_compute_car_id', store=True, readonly=False, tracking=True,
    )

    @api.depends('sale_id.car_id')
    def _compute_car_id(self):
        for picking in self:
            picking.car_id = picking.sale_id.car_id or picking.car_id

    # ---- Rule: Return needs signed delivery slip -------------------------------------------
    def _check_signed_delivery_slip_attached(self):
        for picking in self.filtered(lambda p: p.picking_type_code == 'outgoing'):
            count = self.env['ir.attachment'].sudo().search_count([
                ('res_model', '=', 'stock.picking'),
                ('res_id', '=', picking.id),
                ('res_field', '=', False),
            ])
            if not count:
                raise UserError(_(
                    "Please attach the Delivery Slip that is signed by the customer before creating a Return."
                ))

    # ---- Rule: Receipts only from a Purchase Order ----------------------------------------
    @api.model
    def _check_receipt_has_purchase_order(self, vals):
        ptype_id = vals.get('picking_type_id') or self.env.context.get('default_picking_type_id')
        ptype = self.env['stock.picking.type'].browse(ptype_id) if ptype_id else self.env['stock.picking.type']
        if not ptype or ptype.code != 'incoming':
            return
        if vals.get('return_id'):
            return  # customer / vendor returns
        location = (self.env['stock.location'].browse(vals['location_id'])
                    if vals.get('location_id') else ptype.default_location_src_id)
        if location and location.usage != 'supplier':
            return  # inter-warehouse / production / customer return flows
        origin = vals.get('origin') or ''
        names = [n.strip() for n in re.split(r'[,;]', origin) if n.strip()]
        if names and self.env['purchase.order'].sudo().search_count([('name', 'in', names)]):
            return
        for key in ('move_ids', 'move_ids_without_package'):
            for cmd in vals.get(key) or []:
                if (isinstance(cmd, (list, tuple)) and len(cmd) > 2
                        and isinstance(cmd[2], dict) and cmd[2].get('purchase_line_id')):
                    return
        raise UserError(_(
            "You cannot create a Receipt manually. Receipts must come from a Purchase Order "
            "(confirm the Purchase Order and use its Receipt)."
        ))

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get('skip_receipt_po_check') and not self.env.su:
            for vals in vals_list:
                self._check_receipt_has_purchase_order(vals)
        return super().create(vals_list)
