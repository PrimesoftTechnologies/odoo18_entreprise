import math
from odoo import api, fields, models

class TimberLog(models.Model):
    _name = 'timber.log'
    _description = 'Timber Log Record'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_received desc, id desc'

    name = fields.Char(string='Log Reference', required=True, copy=False, readonly=True, default=lambda self: self.env['ir.sequence'].next_by_code('timber.log'))
    
    wood_type = fields.Selection([
        ('select', 'MTIKI')
    ], string='Wood Type', default='select', required=True)

    vendor_id = fields.Many2one('res.partner', string='Vendor', domain=[('supplier_rank', '>', 0)])
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order')
    receipt_id = fields.Many2one('stock.picking', string='Receipt / Goods Receipt')
    date_received = fields.Date(string='Date Received', default=fields.Date.today, required=True)
    location_id = fields.Many2one('stock.location', string='Location / Warehouse')
    user_id = fields.Many2one('res.users', string='Responsible Person', default=lambda self: self.env.user)
    
    measurement_ids = fields.One2many('timber.log.measurement', 'log_id', string='Log Measurements')
    processing_ids = fields.One2many('timber.processing', 'log_id', string='Processing Orders')
    
    total_circumference = fields.Float(string='Circumference (cm)', compute='_compute_totals', store=True)
    total_length = fields.Float(string='Length (cm)', compute='_compute_totals', store=True)
    total_cbm = fields.Float(string='Total Log CBM (Received CBM)', compute='_compute_totals', store=True, digits=(16, 6))
    
    # --- JUMLA YA BODI ZILIZOBAKI GHALANI (AVAILABLE BOARD CBM) ---
    available_board_cbm = fields.Float(
        string='Available Board CBM', 
        compute='_compute_available_board_cbm', 
        store=True, 
        digits=(16, 4)
    )
    
    # --- SEHEMU YA EXPENSES NA UNUNUZI ---
    purchase_amount = fields.Float(string='Log Purchase Amount', digits=(16, 2))
    fuel_cost = fields.Float(string='Fuel Cost (Mafuta)', digits=(16, 2))
    transport_cost = fields.Float(string='Transport Cost (Usafiri)', digits=(16, 2))
    food_cost = fields.Float(string='Food Cost (Chakula)', digits=(16, 2))
    other_cost = fields.Float(string='Other Expenses', digits=(16, 2))
    
    total_expense = fields.Float(string='Total Operational Expenses', compute='_compute_total_expense', store=True, digits=(16, 2))
    grand_total_cost = fields.Float(string='Grand Total Cost', compute='_compute_grand_total', store=True, digits=(16, 2))

    # --- SEHEMU YA TRANSIT PASS (TP FORM FIELDS ZOTE MPYA) ---
    tp_number = fields.Char(string='TP Number', tracking=True)
    tp_office_seal = fields.Char(string='Office of the (Seal)', tracking=True)
    tp_number_ref = fields.Char(string='Number', tracking=True)
    tp_date = fields.Date(string='Date', tracking=True)
    tp_due_date = fields.Date(string='Due Date', tracking=True)
    tp_purchaser = fields.Char(string='Purchaser Name', tracking=True)
    tp_licence_type = fields.Char(string='Type of Licence', tracking=True)
    
    tp_transport_mode = fields.Selection([
        ('road', 'Road'),
        ('air', 'Air'),
        ('water', 'Water')
    ], string='Mode of Transport', default='road', tracking=True)
    
    tp_vehicle_no = fields.Char(string='Vehicle Number', tracking=True)
    tp_estimated_distance = fields.Char(string='Estimated Distance', tracking=True)
    tp_expired_date = fields.Date(string='Expired Date', tracking=True)
    tp_registration_no = fields.Char(string='Registration Number', tracking=True)
    
    tp_produce_desc = fields.Char(string='Description of Forest Produced', tracking=True)
    tp_species_size = fields.Char(string='Species and Size of Individual logs', tracking=True)
    tp_quantity = fields.Char(string='Quantity', tracking=True)
    tp_forest_origin = fields.Char(string='Name of Forest (town of origin)', tracking=True)
    tp_town_district = fields.Char(string='Name town/district', tracking=True)
    tp_marker_name = fields.Char(string='Marker Name', tracking=True)
    tp_designation = fields.Char(string='Designation', tracking=True)
    tp_station = fields.Char(string='Station', tracking=True)
    tp_indicator_a = fields.Char(string='Indicator "A"', tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('received', 'Received / Measured'),
        ('processing', 'In Sawing'),
        ('done', 'Processed'),
        ('cancel', 'Cancelled')
    ], string='Status', default='draft')

    @api.depends('measurement_ids.cbm', 'measurement_ids.circumference', 'measurement_ids.length')
    def _compute_totals(self):
        for log in self:
            cbm = sum(log.measurement_ids.mapped('cbm'))
            circ = sum(log.measurement_ids.mapped('circumference'))
            length = sum(log.measurement_ids.mapped('length'))
            log.total_cbm = cbm
            log.total_circumference = circ
            log.total_length = length

    @api.depends('processing_ids.board_ids.status', 'processing_ids.board_ids.cbm')
    def _compute_available_board_cbm(self):
        for log in self:
            # Tunachukua bodi zote za gogo hili ambazo bado zipo 'available' ghalani
            available_boards = log.processing_ids.mapped('board_ids').filtered(lambda b: b.status == 'available')
            log.available_board_cbm = sum(available_boards.mapped('cbm'))

    @api.depends('fuel_cost', 'transport_cost', 'food_cost', 'other_cost')
    def _compute_total_expense(self):
        for rec in self:
            rec.total_expense = rec.fuel_cost + rec.transport_cost + rec.food_cost + rec.other_cost

    @api.depends('total_expense', 'purchase_amount')
    def _compute_grand_total(self):
        for rec in self:
            rec.grand_total_cost = rec.purchase_amount + rec.total_expense

    def action_receive(self):
        self.state = 'received'

    def action_process(self):
        self.state = 'processing'


class TimberLogMeasurement(models.Model):
    _name = 'timber.log.measurement'
    _description = 'Log Measurement Details'

    log_id = fields.Many2one('timber.log', string='Log Reference', required=True, ondelete='cascade')
    name = fields.Char(string='Measurement Ref', default='Logs Measurement')
    
    circumference = fields.Float(string='Circumference (cm)', required=True, digits=(16, 2))
    length = fields.Float(string='Length (cm)', required=True, digits=(16, 2))
    cbm = fields.Float(string='Log CBM', compute='_compute_cbm', store=True, digits=(16, 6))

    @api.depends('circumference', 'length')
    def _compute_cbm(self):
        for rec in self:
            if rec.circumference and rec.length:
                rec.cbm = ((rec.circumference ** 2) * rec.length) / 12566370.0
            else:
                rec.cbm = 0.0