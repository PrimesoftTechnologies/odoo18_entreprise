from odoo import models, fields, api


class PhoneTradeIn(models.Model):
    _name = 'phone.trade.in'
    _description = 'Phone Trade-In / Exchange'
    _order = 'id desc'

    # =========================================================
    # REFERENCE
    # =========================================================

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default='New'
    )

    # =========================================================
    # CUSTOMER DETAILS
    # =========================================================

    customer_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True
    )

    customer_phone = fields.Char(
        string='Customer Phone',
        related='customer_id.phone',
        store=True,
        readonly=True
    )

    # =========================================================
    # OLD PHONE DETAILS
    # =========================================================

    old_phone_model = fields.Char(
        string='Old Phone Model',
        required=True
    )

    old_phone_brand_id = fields.Many2one(
        'phone.brand',
        string='Old Phone Brand',
        required=True
    )

    old_phone_imei_1 = fields.Char(
        string='Old Phone IMEI 1',
        required=True,
        index=True
    )

    old_phone_imei_2 = fields.Char(
        string='Old Phone IMEI 2'
    )

    old_phone_serial_number = fields.Char(
        string='Old Phone Serial Number'
    )

    old_phone_condition_id = fields.Many2one(
        'phone.condition',
        string='Old Phone Condition',
        required=True
    )

    old_phone_storage = fields.Char(
        string='Storage'
    )

    old_phone_battery_health = fields.Char(
        string='Battery Health'
    )

    old_phone_accessories = fields.Char(
        string='Accessories'
    )

    old_phone_physical_condition = fields.Text(
        string='Physical Condition'
    )

    old_phone_notes = fields.Text(
        string='Old Phone Notes'
    )

    # =========================================================
    # TRADE-IN VALUATION
    # =========================================================

    estimated_value = fields.Float(
        string='Estimated Value (TSh)',
        default=0.0
    )

    adjustment_amount = fields.Float(
        string='Adjustment / Discount (TSh)',
        default=0.0
    )

    trade_in_value = fields.Float(
        string='Final Trade-In Value (TSh)',
        required=True
    )

    # =========================================================
    # NEW PHONE
    # =========================================================

    new_phone_id = fields.Many2one(
        'phone.stock',
        string='New Phone',
        required=True
    )

    new_phone_model = fields.Char(
        string='New Phone Model',
        related='new_phone_id.model_name',
        store=True,
        readonly=True
    )

    new_phone_imei_1 = fields.Char(
        string='New Phone IMEI 1',
        related='new_phone_id.imei_1',
        store=True,
        readonly=True
    )

    new_phone_imei_2 = fields.Char(
        string='New Phone IMEI 2',
        related='new_phone_id.imei_2',
        store=True,
        readonly=True
    )

    new_phone_price = fields.Float(
        string='New Phone Price (TSh)',
        related='new_phone_id.selling_price',
        store=True,
        readonly=True
    )

    # =========================================================
    # PAYMENT / AMOUNT
    # =========================================================

    amount_to_pay = fields.Float(
        string='Amount to Pay (TSh)',
        compute='_compute_amount_to_pay',
        store=True
    )

    amount_paid = fields.Float(
        string='Amount Paid (TSh)',
        default=0.0
    )

    balance = fields.Float(
        string='Balance (TSh)',
        compute='_compute_balance',
        store=True
    )

    payment_method = fields.Selection(
        [
            ('cash', 'Cash'),
            ('mpesa', 'M-Pesa'),
            ('tigopesa', 'Tigo Pesa'),
            ('airtel_money', 'Airtel Money'),
            ('halopesa', 'HaloPesa'),
            ('bank', 'Bank'),
            ('other', 'Other'),
        ],
        string='Payment Method'
    )

    payment_reference = fields.Char(
        string='Payment Reference'
    )

    # =========================================================
    # DATE
    # =========================================================

    date = fields.Datetime(
        string='Exchange Date',
        default=fields.Datetime.now,
        required=True
    )

    # =========================================================
    # STATUS / WORKFLOW
    # =========================================================

    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('evaluation', 'Evaluation'),
            ('approved', 'Approved'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled'),
        ],
        string='Status',
        default='draft',
        required=True
    )

    # =========================================================
    # NOTES
    # =========================================================

    notes = fields.Text(
        string='Notes'
    )

    # =========================================================
    # COMPUTE AMOUNT TO PAY
    # =========================================================

    @api.depends(
        'new_phone_price',
        'trade_in_value'
    )
    def _compute_amount_to_pay(self):
        for record in self:
            record.amount_to_pay = max(
                record.new_phone_price - record.trade_in_value,
                0.0
            )

    # =========================================================
    # COMPUTE BALANCE
    # =========================================================

    @api.depends(
        'amount_to_pay',
        'amount_paid'
    )
    def _compute_balance(self):
        for record in self:
            record.balance = max(
                record.amount_to_pay - record.amount_paid,
                0.0
            )

    # =========================================================
    # CREATE
    # =========================================================

    @api.model_create_multi
    def create(self, vals_list):

        for vals in vals_list:

            if vals.get('name', 'New') == 'New':

                vals['name'] = (
                    self.env['ir.sequence'].next_by_code(
                        'phone.trade.in'
                    )
                    or 'New'
                )

        return super().create(vals_list)

    # =========================================================
    # WORKFLOW ACTIONS
    # =========================================================

    def action_start_evaluation(self):

        for record in self:
            record.state = 'evaluation'

    def action_approve(self):

        for record in self:
            record.state = 'approved'

    def action_complete(self):

        for record in self:
            record.state = 'completed'

    def action_cancel(self):

        for record in self:
            record.state = 'cancelled'

    def action_reset_to_draft(self):

        for record in self:
            record.state = 'draft'