from odoo import models, fields, api, _
from odoo.exceptions import UserError


class TransportRoute(models.Model):
    _name = 'transport.route'
    _description = 'Transport Route'

    name = fields.Char(required=True)
    source = fields.Char()
    destination = fields.Char()


class TransportAssignment(models.Model):
    _name = 'transport.assignment'
    _description = 'Transport Assignment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name desc, id desc'

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('transport.assignment') or 'New'
        return super().create(vals)

    # HEADER
    name = fields.Char(default='New', readonly=True, copy=False, tracking=True)

    shipping_order_id = fields.Many2one('shipping.order')
    partner_id = fields.Many2one('res.partner', string="Customer")

    route_id = fields.Many2one('transport.route', required=True)

    transfer_type = fields.Selection([
        ('customer', 'Delivery to Customer'),
        ('internal', 'Internal Transfer'),
        ('port', 'Port / Airport'),
    ], default='customer', required=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('done', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], default='draft', tracking=True)

    trip_date = fields.Date(default=fields.Date.today, required=True)
    departure_datetime = fields.Datetime()
    arrival_datetime = fields.Datetime()
    customer_po_number = fields.Char(string="Customer PO Number")

    # DESTINATION
    delivery_address_id = fields.Many2one('res.partner')
    dest_warehouse_id = fields.Many2one('stock.warehouse')

    # INTERNAL LOCATIONS
    source_location_id = fields.Many2one('stock.location')
    destination_location_id = fields.Many2one('stock.location')


    currency_id = fields.Many2one(
        'res.currency',
        related='shipping_order_id.currency_id',
        store=True
    )

    total_amount = fields.Monetary(
        compute='_compute_total',
        store=True,
        currency_field='currency_id'
    )

    invoice_id = fields.Many2one('account.move', readonly=True)

    notes = fields.Text()

    line_ids = fields.One2many(
        'transport.assignment.line',
        'assignment_id',
        string='Vehicle Lines'
    )

    # ─────────────────────────
    # ONCHANGE
    # ─────────────────────────
    @api.onchange('shipping_order_id')
    def _onchange_shipping_order(self):
        if self.shipping_order_id:
            self.partner_id = self.shipping_order_id.consignee_id

    # ─────────────────────────
    # CONSTRAINT
    # ─────────────────────────
    @api.constrains('shipping_order_id', 'partner_id')
    def _check_partner(self):
        for rec in self:
            if not rec.shipping_order_id and not rec.partner_id:
                raise UserError(_("Either Shipping Order or Customer must be set."))

    # ─────────────────────────
    # COMPUTE
    # ─────────────────────────
    @api.depends('line_ids.amount')
    def _compute_total(self):
        for rec in self:
            rec.total_amount = sum(rec.line_ids.mapped('amount'))

    # ─────────────────────────
    # ACTIONS
    # ─────────────────────────
    def action_confirm(self):

        on_trip_state = self.env['fleet.vehicle.state'].search([
            ('name', '=', 'Reserved')
        ], limit=1)

        for rec in self:
            if not rec.line_ids:
                raise UserError(_("Add at least one vehicle line."))

            if rec.transfer_type == 'internal':
                if not rec.source_location_id or not rec.destination_location_id:
                    raise UserError(_("Source and Destination locations are required."))

            for line in rec.line_ids:
                if line.vehicle_id_truck and on_trip_state:
                    line.vehicle_id_truck.state_id = on_trip_state.id          

            rec.state = 'confirmed'

    def action_start(self):

        on_trip_state = self.env['fleet.vehicle.state'].search([
            ('name', '=', 'On Trip')
        ], limit=1)

        for rec in self:
            for line in rec.line_ids:
                if line.vehicle_id_truck and on_trip_state:
                    line.vehicle_id_truck.state_id = on_trip_state.id

            rec.write({
                'state': 'in_progress',
                'departure_datetime': fields.Datetime.now()
            })

    def action_done(self):

        on_trip_state = self.env['fleet.vehicle.state'].search([
            ('name', '=', 'Ready for Dispatch')
        ], limit=1)

        for rec in self:
            rec._create_invoice()

            # CREATE INTERNAL TRANSFER
            if rec.transfer_type == 'internal':
                rec._create_internal_transfer()

            for line in rec.line_ids:
                if line.vehicle_id_truck and on_trip_state:
                    line.vehicle_id_truck.state_id = on_trip_state.id


            
        
            rec.write({
                'state': 'done',
                'arrival_datetime': fields.Datetime.now()
            })

    def action_cancel(self):
        self.write({'state': 'draft'})

    # ─────────────────────────
    # STOCK TRANSFER
    # ─────────────────────────
    def _create_internal_transfer(self):
        self.ensure_one()

        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'internal')
        ], limit=1)

        if not picking_type:
            raise UserError(_("No internal picking type found."))

        moves = []
        for line in self.line_ids:
            if not line.product_id:
                continue

            moves.append((0, 0, {
                'name': line.product_id.display_name,
                'product_id': line.product_id.id,
                'product_uom_qty': line.quantity,
                'product_uom': line.product_id.uom_id.id,
                'location_id': self.source_location_id.id,
                'location_dest_id': self.destination_location_id.id,
            }))

        picking = self.env['stock.picking'].create({
            'picking_type_id': picking_type.id,
            'location_id': self.source_location_id.id,
            'location_dest_id': self.destination_location_id.id,
            'origin': self.name,
            'move_ids_without_package': moves,
        })

        picking.action_confirm()


    # ─────────────────────────
    # INVOICE
    # ─────────────────────────
    def _create_invoice(self):
        self.ensure_one()

        if self.invoice_id:
            return

        if not self.line_ids:
            raise UserError(_("No lines to invoice."))


        # fetch the single configured sale tax
        sale_tax = self.env['account.tax'].search([
            ('type_tax_use', '=', 'sale'),
            ('company_id', '=', self.env.company.id),
        ], limit=1)

        lines = []
        for l in self.line_ids:
            name = "%s | %s - %s" % (
                l.vehicle_id_truck.license_plate or '',
                l.vehicle_id_trailer.license_plate or '',
                l.product_id.display_name or '',
            )

            lines.append((0, 0, {
                'name': name,
                'quantity': l.quantity or 1,
                'price_unit': l.rate,
                'dn_number': l.dn_number,
                'tax_ids': [(6, 0, sale_tax.ids)],
            }))

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_origin': self.name,
            'invoice_line_ids': lines,
            'route_name': self.route_id.name or '',
            'po_no': self.customer_po_number or '',
        })

        self.invoice_id = invoice.id

    def action_view_invoice(self):
        self.ensure_one()
        if not self.invoice_id:
            raise UserError(_("No invoice yet."))

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.invoice_id.id,
        }


# ─────────────────────────────────────────
# VEHICLE LINE
# ─────────────────────────────────────────
class TransportAssignmentLine(models.Model):
    _name = 'transport.assignment.line'
    _description = 'Transport Assignment Line'

    assignment_id = fields.Many2one('transport.assignment', required=True, ondelete='cascade')

    vehicle_id_truck = fields.Many2one('fleet.vehicle',
        required=True, 
        string='Truck',
        domain="[('state_id.name', '=', 'Ready for Dispatch')]"
    )

    vehicle_id_trailer = fields.Many2one(
        'fleet.vehicle',
        string='Trailer',
        domain="[('state_id.name', '=', 'Ready for Dispatch')]"
    )
    driver_id = fields.Many2one(
        'res.partner',
        related='vehicle_id_truck.driver_id',
        store=True,
        readonly=True
    )

    product_id = fields.Many2one(
        'product.product',
        domain=[('is_transport_product', '=', True)],
        string="Product"
    )

    analytic_account_id = fields.Many2one('account.analytic.account')

    dn_number = fields.Char(string="DN Number")
    quantity = fields.Float(string="Tonnage")
    rate = fields.Float()

    amount = fields.Monetary(compute='_compute_amount', store=True)

    currency_id = fields.Many2one(
        related='assignment_id.currency_id',
        store=True
    )


    @api.depends('quantity', 'rate')
    def _compute_amount(self):
        for rec in self:
            rec.amount = rec.quantity * rec.rate


# ─────────────────────────────────────────
# WIZARD
# ─────────────────────────────────────────
class TransportWizard(models.TransientModel):
    _name = 'transport.wizard'
    _description = 'Create Transport Assignment'

    shipping_order_id = fields.Many2one('shipping.order')
    route_id = fields.Many2one('transport.route', required=True)
    trip_date = fields.Date(default=fields.Date.today)

    def action_confirm(self):
        self.ensure_one()

        transport = self.env['transport.assignment'].create({
            'shipping_order_id': self.shipping_order_id.id,
            'route_id': self.route_id.id,
            'trip_date': self.trip_date,
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'transport.assignment',
            'view_mode': 'form',
            'res_id': transport.id,
        }


# ─────────────────────────────────────────
# PRODUCT EXTENSION
# ─────────────────────────────────────────
class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_transport_product = fields.Boolean(string="Is Transport Product")

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    transport_assignment_id = fields.Many2one('transport.assignment')