from odoo import models, fields, api
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta


class PhoneDebt(models.Model):
    _name = 'phone.debt'
    _description = 'Phone Debt / Installment Plan'
    _rec_name = 'name'
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
    # CUSTOMER
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
    # PHONE
    # =========================================================

    phone_id = fields.Many2one(
        'phone.stock',
        string='Phone'
    )

    phone_description = fields.Char(
        string='Phone Description',
        help='e.g. iPhone 13 Pro 128GB'
    )

    # =========================================================
    # FINANCIAL
    # =========================================================

    total_amount = fields.Float(
        string='Total Amount (TSh)',
        required=True,
        default=0.0
    )

    down_payment = fields.Float(
        string='Down Payment (TSh)',
        default=0.0
    )

    financed_amount = fields.Float(
        string='Financed Amount (TSh)',
        compute='_compute_financed_amount',
        store=True,
        help='Amount after down payment (before interest)'
    )

    interest_rate = fields.Float(
        string='Interest Rate (%)',
        default=0.0,
        help='Interest rate applied to financed amount'
    )

    interest_amount = fields.Float(
        string='Interest Amount (TSh)',
        compute='_compute_interest_amount',
        store=True,
        help='Computed interest in TSh'
    )

    total_financed = fields.Float(
        string='Total Financed (TSh)',
        compute='_compute_total_financed',
        store=True,
        help='Financed amount + interest'
    )

    paid_amount = fields.Float(
        string='Paid Amount (TSh)',
        compute='_compute_paid_amount',
        store=True
    )

    balance = fields.Float(
        string='Balance (TSh)',
        compute='_compute_balance',
        store=True
    )

    num_installments = fields.Integer(
        string='Number of Installments',
        required=True,
        default=1
    )

    installment_amount = fields.Float(
        string='Installment Amount (TSh)',
        compute='_compute_installment_amount',
        store=True
    )

    # =========================================================
    # INTERVAL TYPE (MPYA)
    # =========================================================

    interval_type = fields.Selection(
        [
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
        ],
        string='Interval Type',
        default='monthly',
        required=True,
        help='How often should installments be paid?'
    )

    # =========================================================
    # DATES
    # =========================================================

    date = fields.Date(
        string='Debt Date',
        default=fields.Date.today,
        required=True
    )

    first_due_date = fields.Date(
        string='First Due Date',
        required=True
    )

    # =========================================================
    # PAYMENT METHOD
    # =========================================================

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
        string='Preferred Payment Method'
    )

    # =========================================================
    # STATUS / WORKFLOW
    # =========================================================

    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('active', 'Active'),
            ('paid', 'Fully Paid'),
            ('overdue', 'Overdue'),
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
    # INSTALLMENTS (One2many)
    # =========================================================

    installment_ids = fields.One2many(
        'phone.installment',
        'debt_id',
        string='Installments'
    )

    installment_count = fields.Integer(
        string='Installments Count',
        compute='_compute_installment_count',
        store=True
    )

    paid_installments = fields.Integer(
        string='Paid Installments',
        compute='_compute_paid_installments',
        store=True
    )

    pending_installments = fields.Integer(
        string='Pending Installments',
        compute='_compute_pending_installments',
        store=True
    )

    # =========================================================
    # COMPUTE: FINANCED AMOUNT (Total − Down Payment)
    # =========================================================

    @api.depends('total_amount', 'down_payment')
    def _compute_financed_amount(self):
        for record in self:
            record.financed_amount = max(
                (record.total_amount or 0.0) - (record.down_payment or 0.0),
                0.0
            )

    # =========================================================
    # COMPUTE: INTEREST AMOUNT (Financed × Rate%)
    # =========================================================

    @api.depends('financed_amount', 'interest_rate')
    def _compute_interest_amount(self):
        for record in self:
            if record.interest_rate and record.interest_rate > 0:
                record.interest_amount = (
                    (record.financed_amount or 0.0) *
                    (record.interest_rate / 100.0)
                )
            else:
                record.interest_amount = 0.0

    # =========================================================
    # COMPUTE: TOTAL FINANCED (Financed + Interest)
    # =========================================================

    @api.depends('financed_amount', 'interest_amount')
    def _compute_total_financed(self):
        for record in self:
            record.total_financed = (
                (record.financed_amount or 0.0) +
                (record.interest_amount or 0.0)
            )

    # =========================================================
    # COMPUTE: PAID AMOUNT
    # =========================================================

    @api.depends('installment_ids.paid_amount', 'down_payment')
    def _compute_paid_amount(self):
        for record in self:
            installments_paid = sum(
                record.installment_ids.mapped('paid_amount')
            )
            record.paid_amount = (record.down_payment or 0.0) + installments_paid

    # =========================================================
    # COMPUTE: BALANCE (Total + Interest − Paid)
    # =========================================================

    @api.depends('total_amount', 'interest_amount', 'paid_amount')
    def _compute_balance(self):
        for record in self:
            total_with_interest = (
                (record.total_amount or 0.0) +
                (record.interest_amount or 0.0)
            )
            record.balance = max(
                total_with_interest - (record.paid_amount or 0.0),
                0.0
            )

    # =========================================================
    # COMPUTE: INSTALLMENT AMOUNT (with interest)
    # =========================================================

    @api.depends('total_financed', 'num_installments')
    def _compute_installment_amount(self):
        for record in self:
            if record.num_installments and record.num_installments > 0:
                record.installment_amount = (
                    (record.total_financed or 0.0) /
                    record.num_installments
                )
            else:
                record.installment_amount = 0.0

    # =========================================================
    # COMPUTE: INSTALLMENT COUNT
    # =========================================================

    @api.depends('installment_ids')
    def _compute_installment_count(self):
        for record in self:
            record.installment_count = len(record.installment_ids)

    # =========================================================
    # COMPUTE: PAID INSTALLMENTS
    # =========================================================

    @api.depends('installment_ids.state')
    def _compute_paid_installments(self):
        for record in self:
            record.paid_installments = len(
                record.installment_ids.filtered(lambda i: i.state == 'paid')
            )

    # =========================================================
    # COMPUTE: PENDING INSTALLMENTS
    # =========================================================

    @api.depends('installment_ids.state')
    def _compute_pending_installments(self):
        for record in self:
            record.pending_installments = len(
                record.installment_ids.filtered(
                    lambda i: i.state in ('pending', 'overdue')
                )
            )

    # =========================================================
    # CREATE
    # =========================================================

    @api.model_create_multi
    def create(self, vals_list):

        for vals in vals_list:

            if vals.get('name', 'New') == 'New':

                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('phone.debt')
                    or 'New'
                )

        return super().create(vals_list)

    # =========================================================
    # HELPER: COMPUTE NEXT DUE DATE
    # =========================================================

    def _get_next_due_date(self, first_date, index, interval_type):
        """
        Compute due date based on interval_type.
        index = 0, 1, 2, ...
        """
        if interval_type == 'daily':
            return first_date + timedelta(days=index)
        elif interval_type == 'weekly':
            return first_date + timedelta(weeks=index)
        else:  # monthly (default)
            return first_date + relativedelta(months=index)

    # =========================================================
    # GENERATE INSTALLMENTS
    # =========================================================

    def action_generate_installments(self):
        """
        Auto-generate installments based on:
        - num_installments
        - first_due_date
        - interval_type (daily / weekly / monthly)
        - total_financed (with interest)
        """

        for record in self:

            # Delete existing installments (only if none are paid)
            paid = record.installment_ids.filtered(lambda i: i.paid_amount > 0)
            if paid:
                continue

            record.installment_ids.unlink()

            if record.num_installments <= 0:
                continue

            # Compute per installment (with interest)
            amount_per_installment = (
                (record.total_financed or 0.0) /
                record.num_installments
            )

            for i in range(record.num_installments):

                due = record._get_next_due_date(
                    record.first_due_date,
                    i,
                    record.interval_type or 'monthly'
                )

                self.env['phone.installment'].create({
                    'debt_id': record.id,
                    'sequence': i + 1,
                    'due_date': due,
                    'amount': amount_per_installment,
                    'state': 'pending',
                })

    # =========================================================
    # WORKFLOW
    # =========================================================

    def action_activate(self):
        for record in self:
            record.state = 'active'

    def action_cancel(self):
        for record in self:
            record.state = 'cancelled'

    def action_reset_to_draft(self):
        for record in self:
            record.state = 'draft'