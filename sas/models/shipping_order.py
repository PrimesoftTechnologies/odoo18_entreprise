from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class ShippingOrder(models.Model):
    """
    Shipping Order - Core model for Clearing, Forwarding & Transport operations.
    Replaces the former manifest.order. Manifests will be used later for tracking.
    """
    _name = 'shipping.order'
    _description = 'Shipping Order'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'name desc, id desc'


    _sql_constraints = [
        (
            'supplier_invoice_no_unique',
            'UNIQUE(supplier_invoice_no)',
            'Supplier Invoice No. must be unique.'
        ),
        (
            'client_po_number_unique',
            'UNIQUE(client_po_number)',
            'Client PO No. must be unique.'
        ),
    ]

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('shipping.order') or 'New'
        return super().create(vals)


    name = fields.Char(
        string='Reference', default='New', readonly=True,
        copy=False, index=True, tracking=True,
    )
    shipper_id = fields.Many2one('res.partner', string='Shipper', required=True, tracking=True)
    consignee_id = fields.Many2one('res.partner', string='Consignee', required=True, tracking=True)
    agent_id = fields.Many2one('res.partner', string='Forwarding Agent', tracking=True)
    customer_relation_user_id = fields.Many2one(
        'res.users', string='Customer Relations Officer',
        default=lambda self: self.env.user, tracking=True,
    )


    order_type = fields.Selection(
        [('import', 'Import'), ('export', 'Export'), ('transit', 'Transit'),('domestic', 'Domestic'),('local delivery', 'Local Delivery'), ('other', 'Others')],
        string='Order Type', required=True, tracking=True,
    )
    transport_mode = fields.Selection(
        [('sea', 'Sea'), ('air', 'Air'), ('land', 'Road')],
        string='Transport Mode', required=True, tracking=True,
    )
    sea_shipment_type = fields.Selection(
        [('fcl', 'FCL – Full Container Load'), ('lcl', 'LCL – Less than Container Load')],
        string='Sea Shipment Type',
    )
    air_shipment_type = fields.Selection(
        [('express', 'Express / Courier'), ('standard', 'Standard / Regular')],
        string='Air Shipment Type',
    )
    land_shipment_type = fields.Selection(
        [('ftl', 'FTL – Full Truck Load'), ('ltl', 'LTL – Less than Truck Load')],
        string='Land Shipment Type',
    )

    # ─────────────────────────────────────────
    # DATES
    # ─────────────────────────────────────────
    order_date = fields.Date(
        string='Order Date', default=fields.Date.today, required=True, tracking=True,
    )
    etd = fields.Datetime(string='ETD (Estimated Departure)', tracking=True)
    atd = fields.Datetime(string='ATD (Actual Departure)')
    eta = fields.Datetime(string='ETA (Estimated Arrival)', tracking=True, required=True)
    ata = fields.Datetime(string='ATA (Actual Arrival)')

    # ─────────────────────────────────────────
    # PORT / VESSEL / FLIGHT
    # ─────────────────────────────────────────
    loading_port_id = fields.Many2one('freight.port', string='Port of Loading', required=True, tracking=True)
    discharging_port_id = fields.Many2one('freight.port', string='Port of Discharge', required=True, tracking=True)
    vessel_flight_name = fields.Char(string='Vessel / Flight Name', tracking=True)
    voyage_flight_number = fields.Char(string='Voyage / Flight Number')

    # ─────────────────────────────────────────
    # DOCUMENTS & REFERENCES
    # ─────────────────────────────────────────
    bl_awb_number = fields.Char(string='B/L / AWB /RCN no', tracking=True)
    bl_awb_date = fields.Date(string='B/L / AWB /RCN Date')
    # file_number = fields.Char(string='File No.')
    # internal_ref = fields.Char(string='Internal Reference No.')
    supplier_invoice_no = fields.Char(string='Supplier Invoice No.', required=True, tracking=True)
    client_po_number = fields.Char(string='Client PO No.', tracking=True, required=True, help="Client Purchase Order Number")
    pad_number = fields.Char(string='PAD No.')
    pad_reg_number = fields.Char(string='PAD Registration No.')
    do_number = fields.Char(string='Delivery Order (DO) No.', tracking=True)
    do_date = fields.Date(string='DO Date')
    do_expiry_date = fields.Date(string='DO Expiry Date')

    # ─────────────────────────────────────────
    # CUSTOMS / DUTY
    # ─────────────────────────────────────────
    assessed_date = fields.Date(string='Assessment Date')
    duty_amount = fields.Monetary(string='Duty Amount', currency_field='currency_id')
    duty_paid_date = fields.Date(string='Duty Paid Date')
    rfd_date = fields.Date(string='RFD Date')

    # ─────────────────────────────────────────
    # FINANCIALS
    # ─────────────────────────────────────────
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
    )
    freight_charges = fields.Monetary(string='Freight Charges', currency_field='currency_id')
    insurance_policy_no = fields.Char(string='Insurance Policy No.')
    insurance_amount = fields.Monetary(string='Insurance Amount', currency_field='currency_id')
    other_charges = fields.Monetary(string='Other Charges', currency_field='currency_id')
    total_amount = fields.Monetary(
        string='Total Amount', compute='_compute_total_amount',
        store=True, currency_field='currency_id',
    )

    # ─────────────────────────────────────────
    # CARGO SUMMARY (computed)
    # ─────────────────────────────────────────
    total_quantity = fields.Float(compute='_compute_cargo_totals', string='Total Qty', store=True)
    total_weight = fields.Float(compute='_compute_cargo_totals', string='Total Weight (kg)', store=True)
    total_volume = fields.Float(compute='_compute_cargo_totals', string='Total Volume (cbm)', store=True)
    total_packages = fields.Integer(compute='_compute_cargo_totals', string='Total Packages', store=True)

    # ─────────────────────────────────────────
    # STATE / STATUS
    # ─────────────────────────────────────────
    state = fields.Selection([
        ('draft',       'Draft'),
        ('submitted',   'Submitted'),
        ('confirmed',   'Confirmed'),
        ('arrived',     'Arrived'),
        ('clearing',    'Clearing'),
        ('cleared',     'Cleared'),
        ('received',    'Stock Received'),
        ('transported', 'Transported'),
        ('delivered',   'Delivered'),
        ('done',        'Done'),
        ('cancelled',   'Cancelled'),
    ], string='Status', default='draft', tracking=True, copy=False)

    is_overdue = fields.Boolean(compute='_compute_is_overdue', string='Overdue', store=False)
    remarks = fields.Text(string='Remarks')

    line_ids = fields.One2many('shipping.order.line', 'order_id', string='Cargo Lines', required=True)

    clearance_ids = fields.One2many('clearance.record', 'shipping_order_id', string='Clearance Records')
    clearance_count = fields.Integer(compute='_compute_clearance_count', string='Clearances')

    transport_id = fields.Many2one('transport.assignment', string='Transport Assignment')

    picking_ids = fields.One2many('stock.picking', 'shipping_order_id', string='GRNs / Receipts')
    picking_count = fields.Integer(compute='_compute_picking_count', string='GRN Count')

    trip_ids = fields.One2many('transport.assignment', 'shipping_order_id', string='Transport Trips')
    trip_count = fields.Integer(compute='_compute_trip_count', string='Transport Trips')

    # ─────────────────────────────────────────
    # COMPUTES
    # ─────────────────────────────────────────
    @api.depends('line_ids.quantity', 'line_ids.weight', 'line_ids.volume', 'line_ids.packages')
    def _compute_cargo_totals(self):
        for order in self:
            order.total_quantity = sum(line.quantity for line in order.line_ids)
            order.total_weight = sum(line.weight for line in order.line_ids)
            order.total_volume = sum(line.volume for line in order.line_ids)
            order.total_packages = sum(line.packages for line in order.line_ids)

    @api.depends('freight_charges', 'insurance_amount', 'other_charges', 'duty_amount')
    def _compute_total_amount(self):
        for order in self:
            order.total_amount = (
                order.freight_charges
                + order.insurance_amount
                + order.other_charges
                + order.duty_amount
            )

    @api.depends('eta', 'state')
    def _compute_is_overdue(self):
        for order in self:
            order.is_overdue = (
                order.eta
                and fields.Datetime.now() > order.eta
                and order.state in ('confirmed', 'arrived', 'clearing')
            )

    def _compute_clearance_count(self):
        for order in self:
            order.clearance_count = len(order.clearance_ids)

    @api.depends('picking_ids')
    def _compute_picking_count(self):
        for order in self:
            order.picking_count = len(order.picking_ids)


    def _compute_trip_count(self):
        for order in self:
            order.trip_count = len(order.trip_ids)

    # ─────────────────────────────────────────
    # CONSTRAINTS
    # ─────────────────────────────────────────
    @api.constrains('etd', 'eta')
    def _check_dates(self):
        for order in self:
            if order.etd and order.eta and order.etd > order.eta:
                raise ValidationError(_("ETD cannot be later than ETA."))

    # ─────────────────────────────────────────
    # STATE ACTIONS
    # ─────────────────────────────────────────

    def action_submit(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError(_("You cannot submitted a Shipping Order without at least one Cargo Line."))

            rec.write({'state': 'submitted'})
            rec.message_post(body=_("Shipping order submitted for confirmation."))

    def action_confirm(self):
        for rec in self:
            rec.write({'state': 'confirmed'})
            rec.message_post(body=_("Shipping order confirmed."))

    def action_arrived(self):
        for rec in self:
            if rec.state != 'confirmed':
                raise UserError(_("Only confirmed orders can be marked as arrived."))
            rec.write({'ata': fields.Datetime.now()})
            rec.message_post(body=_("Cargo has arrived."))

    def action_start_clearing(self):
        """Opens Clearing Wizard – transitions to 'clearing' state upon wizard confirm."""
        self.ensure_one()
        return {
            'name': _('Start Clearing Process'),
            'type': 'ir.actions.act_window',
            'res_model': 'clearing.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_shipping_order_id': self.id},
        }

    def action_cleared(self):
        for rec in self:
            rec.write({'state': 'cleared'})
            rec.message_post(body=_("Customs clearance completed."))

    def action_received_products(self):
        """Create a GRN (incoming stock picking) and transition to 'received'."""
        self.ensure_one()
        if self.state != 'cleared':
            raise UserError(_("Order must be cleared before receiving products into stock."))

        picking_type_in = self.env.ref('stock.picking_type_in')
        picking = self.env['stock.picking'].sudo().create({
            'partner_id': self.shipper_id.id,
            'shipping_order_id': self.id,
            'picking_type_id': picking_type_in.id,
            'location_id': picking_type_in.default_location_src_id.id,
            'location_dest_id': picking_type_in.default_location_dest_id.id,
            'origin': self.name,
        })
        for line in self.line_ids:
            if not line.product_id:
                continue
            self.env['stock.move'].sudo().create({
                'picking_id': picking.id,
                'name': line.product_id.name,
                'product_id': line.product_id.id,
                'product_uom_qty': line.quantity,
                'product_uom': line.uom_id.id,
                'location_id': picking.location_id.id,
                'location_dest_id': picking.location_dest_id.id,
            })
        picking.sudo().action_confirm()
        picking.sudo().action_assign()

        self.write({'state': 'received'})
        self.message_post(body=_("Products received into stock. GRN created: %s") % picking.name)

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'res_id': picking.id,
            'target': 'current',
        }

    def action_open_transport_wizard(self):
        self.ensure_one()
        return {
            'name': _('Create Transport Assignment'),
            'type': 'ir.actions.act_window',
            'res_model': 'transport.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_shipping_order_id': self.id},
        }

    def action_delivered(self):
        for rec in self:
            if rec.state != 'transported':
                raise UserError(_("Order must be in 'Transported' state to mark as delivered."))
            rec.write({'state': 'delivered'})
            rec.message_post(body=_("Cargo delivered to consignee."))


    def action_done(self):
        for rec in self:
            if rec.state != 'transported':
                raise UserError(_("Order must be transported before marking as done."))
            rec.write({'state': 'done'})
            rec.message_post(body=_("Shipping order completed and closed."))

    def action_cancel(self):
        for rec in self:
            if rec.state in ('done', 'transported'):
                raise UserError(_("Cannot cancel a completed or transported order."))
            rec.write({'state': 'cancelled'})
            rec.message_post(body=_("Order cancelled."))

    def action_reset_draft(self):
        for rec in self:
            if rec.state != 'cancelled':
                raise UserError(_("Only cancelled orders can be reset to draft."))
            rec.write({'state': 'draft'})
            rec.message_post(body=_("Order reset to draft."))

    # ─────────────────────────────────────────
    # SMART BUTTON ACTIONS
    # ─────────────────────────────────────────
    def action_view_clearances(self):
        self.ensure_one()

        clearance = self.env['clearance.record'].search([
            ('shipping_order_id', '=', self.id)
        ], limit=1)

        return {
            'name': _('Clearance Record'),
            'type': 'ir.actions.act_window',
            'res_model': 'clearance.record',
            'view_mode': 'form',
            'res_id': clearance.id,
            'target': 'current',
            'context': {'default_shipping_order_id': self.id},
        }

    def action_view_pickings(self):
        self.ensure_one()
        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        action['domain'] = [('shipping_order_id', '=', self.id)]
        action['context'] = {
            'default_partner_id': self.consignee_id.id,
            'default_shipping_order_id': self.id,
            'default_picking_type_id': self.env.ref('stock.picking_type_in').id,
        }
        if self.picking_count == 1:
            action['views'] = [(self.env.ref('stock.view_picking_form').id, 'form')]
            action['res_id'] = self.picking_ids.id
        return action

    def action_view_transport(self):
        self.ensure_one()
        if not self.transport_id:
            raise UserError(_("No transport assignment linked yet."))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'transport.assignment',
            'view_mode': 'form',
            'res_id': self.transport_id.id,
            'target': 'current',
        }

    def action_view_trips(self):
        self.ensure_one()

        action = self.env.ref('sas.action_transport_assignment').read()[0]
        action['domain'] = [('shipping_order_id', '=', self.id)]
        action['context'] = {'default_shipping_order_id': self.id}
        if self.trip_count == 1:
            action['views'] = [(self.env.ref('sas.action_transport_assignment').id, 'form')]
            action['res_id'] = self.trip_ids.id
        return action




# ──────────────────────────────────────────────────────────────────
class ShippingOrderLine(models.Model):
    """Cargo line items on a Shipping Order."""
    _name = 'shipping.order.line'
    _description = 'Shipping Order Line'

    order_id = fields.Many2one('shipping.order', string='Shipping Order', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product')
    cargo_description = fields.Char(string='Cargo Description')
    hs_code = fields.Char(string='HS Code')
    packages = fields.Integer(string='Packages')
    package_type = fields.Char(string='Package Type (e.g. Carton, Pallet)')
    container_number = fields.Char(string='Container No.')
    container_type = fields.Char(string='Container Type')
    seal_number = fields.Char(string='Seal No.')
    quantity = fields.Float(string='Quantity', digits='Product Unit of Measure')
    uom_id = fields.Many2one('uom.uom', related='product_id.uom_id', string='UoM', readonly=True)
    weight = fields.Float(string='Weight (kg)', digits='Stock Weight')
    volume = fields.Float(string='Volume (cbm)')
    unit_value = fields.Monetary(string='Unit Value', currency_field='currency_id')
    total_value = fields.Monetary(
        string='Total Value', currency_field='currency_id',
        compute='_compute_total_value', store=True,
    )
    country_of_origin = fields.Many2one('res.country', string='Country of Origin')
    currency_id = fields.Many2one('res.currency', related='order_id.currency_id')

    @api.depends('unit_value', 'quantity')
    def _compute_total_value(self):
        for line in self:
            line.total_value = line.unit_value * line.quantity


# ──────────────────────────────────────────────────────────────────
# ORM EXTENSIONS – inherit existing Odoo models
# ──────────────────────────────────────────────────────────────────
class StockPicking(models.Model):
    _inherit = 'stock.picking'
    shipping_order_id = fields.Many2one('shipping.order', string='Shipping Order', index=True)


class AccountMove(models.Model):
    _inherit = 'account.move'
    shipping_order_id = fields.Many2one('shipping.order', string='Shipping Order', index=True)


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    dn_number = fields.Char(string="DN Number")


class AccountPayment(models.Model):
    _inherit = 'account.payment'
    shipping_order_id = fields.Many2one('shipping.order', string='Shipping Order', index=True)