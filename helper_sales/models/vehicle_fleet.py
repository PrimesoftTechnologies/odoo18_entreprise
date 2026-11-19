# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class SaleOrderVehicle(models.Model):
    _inherit = 'sale.order'

    # old list of cars (kept only for history)
    car_id = fields.Many2one(string='Car (Old)', required=False)

    # Car Number now comes from the Fleet module
    vehicle_id = fields.Many2one('fleet.vehicle', string='Car Number', tracking=True, copy=True)

    # Only ONE driver: shown as a single choice, stored in driver_ids (so reports and invoices keep working)
    current_driver_id = fields.Many2one(
        'sale.driver', string='Driver',
        compute='_compute_current_driver', inverse='_inverse_current_driver')

    @api.depends('driver_ids')
    def _compute_current_driver(self):
        for order in self:
            order.current_driver_id = order.driver_ids[:1]

    def _inverse_current_driver(self):
        for order in self:
            order.driver_ids = [(6, 0, order.current_driver_id.ids)]

    @api.constrains('driver_ids')
    def _check_one_driver(self):
        for order in self:
            if len(order.driver_ids) > 1:
                raise ValidationError(_("Only one Driver is allowed on %s.", order.name))

    def _prepare_invoice(self):
        vals = super()._prepare_invoice()
        vals['vehicle_id'] = self.vehicle_id.id
        return vals

    def action_confirm(self):
        for order in self:
            if not order.vehicle_id:
                raise UserError(_("Car Number is required on %s.", order.name))
        return super().action_confirm()


class AccountMoveVehicle(models.Model):
    _inherit = 'account.move'

    vehicle_id = fields.Many2one('fleet.vehicle', string='Car Number', tracking=True, copy=False)
    current_driver_id = fields.Many2one(
        'sale.driver', string='Driver',
        compute='_compute_current_driver', inverse='_inverse_current_driver')

    @api.depends('driver_ids')
    def _compute_current_driver(self):
        for move in self:
            move.current_driver_id = move.driver_ids[:1]

    def _inverse_current_driver(self):
        for move in self:
            move.driver_ids = [(6, 0, move.current_driver_id.ids)]

    @api.constrains('driver_ids')
    def _check_one_driver(self):
        for move in self:
            if len(move.driver_ids) > 1:
                raise ValidationError(_("Only one Driver is allowed on %s.", move.display_name))


class StockPickingVehicle(models.Model):
    _inherit = 'stock.picking'

    vehicle_id = fields.Many2one(
        'fleet.vehicle', string='Car Number',
        compute='_compute_vehicle_id', store=True, readonly=False, tracking=True)

    @api.depends('sale_id.vehicle_id')
    def _compute_vehicle_id(self):
        for picking in self:
            picking.vehicle_id = picking.sale_id.vehicle_id or picking.vehicle_id


class FleetVehicleOptionalModel(models.Model):
    _inherit = 'fleet.vehicle'

    # A vehicle can be registered with only its plate number (no brand / model needed)
    model_id = fields.Many2one(required=False)

    @api.depends('model_id.brand_id.name', 'model_id.name', 'license_plate')
    def _compute_vehicle_name(self):
        for record in self:
            parts = [record.model_id.brand_id.name, record.model_id.name, record.license_plate or _('No Plate')]
            record.name = '/'.join(part for part in parts if part)
