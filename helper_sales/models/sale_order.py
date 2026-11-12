# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleCar(models.Model):
    _name = 'sale.car'
    _description = 'Sales Car'
    _rec_name = 'name'

    name = fields.Char(string='Car Number', required=True)
    model_name = fields.Char(string='Car Model')


class SaleRegion(models.Model):
    _name = 'sale.region'
    _description = 'Sales Region'
    _rec_name = 'name'

    name = fields.Char(string='Region Name', required=True)
    code = fields.Char(string='Region Code')


class SaleDriver(models.Model):
    _name = 'sale.driver'
    _description = 'Driver'
    _order = 'name'

    name = fields.Char(string='Driver Name', required=True)
    phone = fields.Char(string='Phone')
    employee_id = fields.Many2one('hr.employee', string='Employee (optional)')
    active = fields.Boolean(default=True)
    is_external = fields.Boolean(
        string='External', default=False, copy=False,
        help="Typed on an order for someone who is not in the list. External names are not shown in the list.")

    @api.model
    def name_create(self, name):
        # A name typed on an order is kept for that order only, it is NOT added to the selectable list
        record = self.create({'name': name, 'is_external': True})
        return record.id, record.display_name


class SaleHelper(models.Model):
    _name = 'sale.helper'
    _description = 'Helper'
    _order = 'name'

    name = fields.Char(string='Helper Name', required=True)
    phone = fields.Char(string='Phone')
    employee_id = fields.Many2one('hr.employee', string='Employee (optional)')
    active = fields.Boolean(default=True)
    is_external = fields.Boolean(
        string='External', default=False, copy=False,
        help="Typed on an order for someone who is not in the list. External names are not shown in the list.")

    @api.model
    def name_create(self, name):
        # A name typed on an order is kept for that order only, it is NOT added to the selectable list
        record = self.create({'name': name, 'is_external': True})
        return record.id, record.display_name


class SaleOrder(models.Model):
    _inherit = "sale.order"

    # Legacy fields
    driver_id = fields.Many2one("hr.employee", string="Driver (Old)")
    helper_ids = fields.Many2many(
        "hr.employee", "sale_order_helper_rel", "order_id", "employee_id",
        string="Helpers (Old)",
    )

    # Old free-text fields (kept only so old data is not lost; not shown on the forms)
    driver_name = fields.Char(string="Driver (Old Text)")
    helper_name = fields.Char(string="Helper (Old Text)")

    # Pick people from the list, or type an outside name (kept on this order only, not added to the list)
    driver_ids = fields.Many2many(
        "sale.driver", "sale_order_sale_driver_rel", "order_id", "driver_id",
        string="Drivers", tracking=True, domain=[('is_external', '=', False)],
    )
    sale_helper_ids = fields.Many2many(
        "sale.helper", "sale_order_sale_helper_rel", "order_id", "helper_id",
        string="Helpers", tracking=True, domain=[('is_external', '=', False)],
    )

    car_id = fields.Many2one("sale.car", string="Car Number", required=True, tracking=True)
    region_id = fields.Many2one("sale.region", string="Region", required=True, tracking=True)

    def _prepare_invoice(self):
        invoice_vals = super()._prepare_invoice()
        invoice_vals.update({
            'driver_ids': [(6, 0, self.driver_ids.ids)],
            'sale_helper_ids': [(6, 0, self.sale_helper_ids.ids)],
            'car_id': self.car_id.id,
            'region_id': self.region_id.id,
        })
        return invoice_vals

    def action_confirm(self):
        for order in self:
            order.partner_id.commercial_partner_id._check_tin_required()
        return super().action_confirm()

    def action_view_invoice(self, invoices=False):
        """ Checks if the customer has an incomplete previous payment before allowing Create Invoice """
        for order in self:
            if order.partner_id:
                unfinished_payment = self.env['account.payment'].search([
                    ('partner_id', '=', order.partner_id.commercial_partner_id.id),
                    ('state', 'in', ['draft', 'in_process'])
                ], limit=1)
                if unfinished_payment:
                    raise UserError(
                        f"This customer ({order.partner_id.name}) has a previous payment that is still incomplete! "
                        "Please complete the previous payment before creating a new invoice."
                    )
        return super().action_view_invoice(invoices)