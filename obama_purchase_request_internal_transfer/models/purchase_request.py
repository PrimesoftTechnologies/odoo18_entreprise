from odoo import api, fields, models, _
from odoo.exceptions import UserError

from .view_utils import inject_request_form

LINE_FIELD_CANDIDATES = ('line_ids', 'request_line_ids', 'purchase_request_line_ids', 'lines')
QTY_CANDIDATES = ('product_qty', 'quantity', 'product_uom_qty', 'qty')
UOM_CANDIDATES = ('product_uom_id', 'product_uom', 'uom_id')


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    is_internal_transfer = fields.Boolean(
        string='Is Internal Transfer',
        compute='_compute_is_internal_transfer',
    )
    transfer_ids = fields.One2many(
        'stock.picking', 'obama_request_id', string='Internal Transfers', copy=False)
    transfer_count = fields.Integer(compute='_compute_transfer_count')
    transfer_requested = fields.Boolean(
        string='Internal Transfer Pressed', copy=False,
        help='Set as soon as the Internal Transfer button is pressed (used for the button colour).')

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == 'form':
            inject_request_form(arch)
        return arch, view

    @api.depends('transfer_ids')
    def _compute_transfer_count(self):
        for rec in self:
            rec.transfer_count = len(rec.transfer_ids)

    @api.depends('picking_type_id', 'picking_type_id.code')
    def _compute_is_internal_transfer(self):
        for rec in self:
            rec.is_internal_transfer = rec.picking_type_id.code == 'internal'

    def _get_request_lines(self):
        self.ensure_one()
        found = None
        for fname, field in self._fields.items():
            if field.type == 'one2many' and 'product_id' in self.env[field.comodel_name]._fields:
                if fname in LINE_FIELD_CANDIDATES:
                    return self[fname]
                found = found or fname
        if not found:
            raise UserError(_('Could not find the request lines.'))
        return self[found]

    @staticmethod
    def _first_field(record, candidates):
        for name in candidates:
            if name in record._fields:
                return name
        return False

    def _prepare_internal_transfer_move_vals(self):
        """Move lines for the new transfer. Locations are intentionally NOT set:
        the user chooses source / destination on the transfer form."""
        self.ensure_one()
        moves = []
        for line in self._get_request_lines():
            if not line.product_id:
                continue
            qty_f = self._first_field(line, QTY_CANDIDATES)
            uom_f = self._first_field(line, UOM_CANDIDATES)
            qty = line[qty_f] if qty_f else 1.0
            uom = (line[uom_f] if uom_f else False) or line.product_id.uom_id
            moves.append((0, 0, {
                'name': line.product_id.display_name,
                'product_id': line.product_id.id,
                'product_uom_qty': qty,
                'product_uom': uom.id,
            }))
        if not moves:
            raise UserError(_('There are no product lines to transfer.'))
        return moves

    def action_view_internal_transfer(self):
        self.ensure_one()
        transfers = self.transfer_ids
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Internal Transfers'),
            'res_model': 'stock.picking',
            'target': 'current',
        }
        if len(transfers) == 1:
            action.update({'view_mode': 'form', 'res_id': transfers.id})
        else:
            action.update({
                'view_mode': 'list,form',
                'domain': [('obama_request_id', '=', self.id)],
                'context': {'create': False},
            })
        return action

    def action_create_internal_transfer(self):
        self.ensure_one()
        if self.picking_type_id.code != 'internal':
            raise UserError(_('The Picking Type must be an Internal Transfer.'))
        # remember the button was pressed -> it turns to a normal (grey) button from now on
        if not self.transfer_requested:
            self.transfer_requested = True
        # Always open a NEW (unsaved) transfer form: a request can have many transfers.
        # Locations stay empty so the user picks source and destination.
        return {
            'type': 'ir.actions.act_window',
            'name': _('Internal Transfer'),
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'current',
            'context': {
                'default_picking_type_id': self.picking_type_id.id,
                'default_origin': self.name,
                'default_obama_request_id': self.id,
                'default_move_ids_without_package': self._prepare_internal_transfer_move_vals(),
                'clear_picking_locations': True,
            },
        }
