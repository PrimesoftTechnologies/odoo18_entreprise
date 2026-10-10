from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import date


class PhonePurchaseOrder(models.Model):
    _name = 'phone.purchase.order'
    _description = 'Phone Purchase Order (RFQ/PO)'
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
    # SUPPLIER
    # =========================================================

    supplier_id = fields.Many2one(
        'res.partner',
        string='Supplier',
        required=True,
        domain="[('supplier_rank', '>', 0)]"
    )

    supplier_phone = fields.Char(
        string='Supplier Phone',
        related='supplier_id.phone',
        store=True,
        readonly=True
    )

    # =========================================================
    # DATES
    # =========================================================

    date_order = fields.Datetime(
        string='Order Date',
        default=fields.Datetime.now,
        required=True
    )

    date_expected = fields.Date(
        string='Expected Delivery',
        default=fields.Date.today
    )

    # =========================================================
    # PAYMENT
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
        string='Payment Method',
        default='cash'
    )

    # =========================================================
    # STATE
    # =========================================================

    state = fields.Selection(
        [
            ('draft', 'RFQ'),
            ('confirmed', 'Purchase Order'),
            ('partial', 'Partially Received'),
            ('received', 'Fully Received'),
            ('invoiced', 'Invoiced'),
            ('paid', 'Paid'),
            ('cancelled', 'Cancelled'),
        ],
        string='Status',
        default='draft',
        required=True
    )

    # =========================================================
    # LINES (One2many)
    # =========================================================

    line_ids = fields.One2many(
        'phone.purchase.order.line',
        'order_id',
        string='Purchase Lines'
    )

    line_count = fields.Integer(
        string='Lines Count',
        compute='_compute_totals',
        store=True
    )

    # =========================================================
    # TOTALS
    # =========================================================

    subtotal = fields.Float(
        string='Subtotal (TSh)',
        compute='_compute_totals',
        store=True
    )

    total = fields.Float(
        string='Total (TSh)',
        compute='_compute_totals',
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

    # =========================================================
    # RECEIVE TRACKING
    # =========================================================

    total_ordered = fields.Integer(
        string='Total Ordered Qty',
        compute='_compute_receive_totals',
        store=True
    )

    total_received = fields.Integer(
        string='Total Received Qty',
        compute='_compute_receive_totals',
        store=True
    )

    total_pending = fields.Integer(
        string='Total Pending Qty',
        compute='_compute_receive_totals',
        store=True
    )

    is_fully_received = fields.Boolean(
        string='Fully Received',
        compute='_compute_receive_totals',
        store=True
    )

    # =========================================================
    # ✅ RECEIVED-BASED PAYMENT (MPYA)
    # =========================================================

    received_amount = fields.Float(
        string='Received Amount (TSh)',
        compute='_compute_received_amount',
        store=True,
        help='Qty iliyopokelewa × unit_price. Hii ni kiasi ambacho supplier '
             'anastahili kulipwa kwa sasa.'
    )

    can_be_paid = fields.Boolean(
        string='Can be Paid',
        compute='_compute_can_be_paid',
        store=True,
        help='True kama kuna kitu cha kulipa (received_amount > amount_paid)'
    )

    # =========================================================
    # NOTES
    # =========================================================

    notes = fields.Text(string='Notes')

    # =========================================================
    # COMPUTE: TOTALS
    # =========================================================

    @api.depends(
        'line_ids',
        'line_ids.subtotal',
        'line_ids.quantity',
        'line_ids.price_unit',
    )
    def _compute_totals(self):
        for record in self:
            record.line_count = len(record.line_ids)
            record.subtotal = sum(record.line_ids.mapped('subtotal'))
            record.total = record.subtotal

    # =========================================================
    # COMPUTE: BALANCE (kwa zilizopokelewa)
    # =========================================================

    @api.depends('received_amount', 'amount_paid')
    def _compute_balance(self):
        for record in self:
            record.balance = max(
                (record.received_amount or 0.0) - (record.amount_paid or 0.0),
                0.0
            )

    # =========================================================
    # COMPUTE: RECEIVE TOTALS + RECEIVED AMOUNT + CAN BE PAID
    # =========================================================

    @api.depends(
        'line_ids.quantity',
        'line_ids.qty_received',
        'line_ids.qty_pending',
        'line_ids.price_unit',
    )
    def _compute_receive_totals(self):
        for record in self:
            record.total_ordered = sum(record.line_ids.mapped('quantity'))
            record.total_received = sum(record.line_ids.mapped('qty_received'))
            record.total_pending = sum(record.line_ids.mapped('qty_pending'))
            record.is_fully_received = (
                record.total_ordered > 0 and
                record.total_pending == 0
            )
            # Pia compute received_amount hapa
            total = 0.0
            for line in record.line_ids:
                total += (line.qty_received or 0) * (line.price_unit or 0.0)
            record.received_amount = total
            record.can_be_paid = (
                record.received_amount > 0 and
                record.amount_paid < record.received_amount
            )

    # =========================================================
    # COMPUTE: RECEIVED AMOUNT (standalone method)
    # =========================================================

    @api.depends(
        'line_ids.qty_received',
        'line_ids.price_unit',
    )
    def _compute_received_amount(self):
        for record in self:
            total = 0.0
            for line in record.line_ids:
                total += (line.qty_received or 0) * (line.price_unit or 0.0)
            record.received_amount = total

    # =========================================================
    # COMPUTE: CAN BE PAID
    # =========================================================

    @api.depends('received_amount', 'amount_paid')
    def _compute_can_be_paid(self):
        for record in self:
            record.can_be_paid = (
                record.received_amount > 0 and
                record.amount_paid < record.received_amount
            )

    # =========================================================
    # CREATE
    # =========================================================

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('phone.purchase.order')
                    or 'New'
                )
        orders = super().create(vals_list)

        for order in orders:
            if order.line_ids:
                order._compute_totals()
                order._compute_balance()
                order._compute_receive_totals()

        return orders

    # =========================================================
    # WRITE — FORCE RECOMPUTE
    # =========================================================

    def write(self, vals):
        result = super().write(vals)

        if 'line_ids' in vals:
            for record in self:
                record._compute_totals()
                record._compute_balance()
                record._compute_receive_totals()

        return result

    # =========================================================
    # WORKFLOW ACTIONS
    # =========================================================

    def action_confirm(self):
        """RFQ → Confirmed PO"""
        for record in self:
            record._compute_totals()
            record._compute_balance()
            record._compute_receive_totals()
            record.state = 'confirmed'

    # =========================================================
    # ACTION: RECEIVE (PER LINE)
    # =========================================================

    def action_receive(self, receive_data=None):
        """
        Receive products per line.
        """

        for record in self:

            # ✅ Ruhusu receive kama bado kuna pending
            if record.total_pending == 0 and record.state in ('received', 'invoiced', 'paid'):
                continue

            # Kama receive_data haipo → receive zote
            if receive_data is None:
                receive_data = {
                    line.id: (line.quantity - line.qty_received)
                    for line in record.line_ids
                    if (line.quantity - line.qty_received) > 0
                }
            else:
                # ✅ CONVERT keys kutoka string → int (muhimu kwa JS call)
                receive_data = {int(k): int(v) for k, v in receive_data.items()}

            for line in record.line_ids:

                qty_now = receive_data.get(line.id, 0)
                qty_now = max(int(qty_now or 0), 0)

                if qty_now == 0:
                    continue

                pending = (line.quantity or 0) - (line.qty_received or 0)
                if qty_now > pending:
                    qty_now = pending

                # =============================================
                # UPDATE STOCK
                # =============================================

                if line.phone_id:
                    existing_phone = line.phone_id
                    existing_phone.quantity = (
                        (existing_phone.quantity or 0) + qty_now
                    )
                else:
                    if not line.brand_id or not line.category_id or not line.condition_id:
                        raise UserError(
                            f"Tafadhali jaza Brand, Category, na Condition "
                            f"kwa phone model '{line.phone_model}'."
                        )

                    new_phone = self.env['phone.stock'].create({
                        'model_name': line.phone_model,
                        'brand_id': line.brand_id.id,
                        'category_id': line.category_id.id,
                        'condition_id': line.condition_id.id,
                        'imei_1': line.imei_1 or f"AUTO-{line.id}",
                        'imei_2': line.imei_2 or False,
                        'buying_price': line.price_unit,
                        'selling_price': line.price_unit * 1.2,
                        'quantity': qty_now,
                        'supplier_id': record.supplier_id.id,
                        'date_received': fields.Date.today(),
                    })

                    line.phone_id = new_phone.id

                # =============================================
                # UPDATE QTY_RECEIVED
                # =============================================

                line.qty_received = (line.qty_received or 0) + qty_now

            # =============================================
            # RECOMPUTE
            # =============================================

            record._compute_totals()
            record._compute_balance()
            record._compute_receive_totals()

            # =============================================
            # STATE LOGIC
            # =============================================

            if record.total_pending == 0:
                # Zote zimepokelewa
                if record.amount_paid >= record.received_amount:
                    record.state = 'paid'
                else:
                    record.state = 'received'
            elif record.total_received > 0:
                # Baadhi zimepokelewa
                record.state = 'partial'
            else:
                record.state = 'confirmed'

    def action_create_invoice(self):
        """Create invoice (Bill)"""
        for record in self:
            if record.total_received > 0:
                record.state = 'invoiced'

    def action_mark_paid(self):
        """Mark as paid — kulipia kiasi cha zilizopokelewa pekee"""
        for record in self:
            record.amount_paid = record.received_amount
            record._compute_balance()
            record._compute_can_be_paid()

            # State:
            if record.total_pending == 0:
                # Zote zimepokelewa + zote zimelipwa
                record.state = 'paid'
            else:
                # Bado kuna pending — ibaki partial/received
                if record.total_received > 0:
                    record.state = 'partial'

    def action_cancel(self):
        for record in self:
            record.state = 'cancelled'

    def action_reset_to_draft(self):
        for record in self:
            record.state = 'draft'


class PhonePurchaseOrderLine(models.Model):
    _name = 'phone.purchase.order.line'
    _description = 'Phone Purchase Order Line'
    _rec_name = 'phone_model'
    _order = 'id asc'

    # =========================================================
    # RELATIONSHIP
    # =========================================================

    order_id = fields.Many2one(
        'phone.purchase.order',
        string='Purchase Order',
        required=True,
        ondelete='cascade'
    )

    # =========================================================
    # PHONE (linked phone.stock — optional)
    # =========================================================

    phone_id = fields.Many2one(
        'phone.stock',
        string='Existing Phone',
        help='Chagua phone iliyopo kwenye stock (kama unarudisha stock).'
    )

    # =========================================================
    # PHONE INFO
    # =========================================================

    phone_model = fields.Char(
        string='Phone Model',
        required=True
    )

    brand_id = fields.Many2one(
        'phone.brand',
        string='Brand',
        required=True
    )

    category_id = fields.Many2one(
        'phone.category',
        string='Category',
        domain="[('brand_id', '=', brand_id)]"
    )

    condition_id = fields.Many2one(
        'phone.condition',
        string='Condition'
    )

    imei_1 = fields.Char(string='IMEI 1')
    imei_2 = fields.Char(string='IMEI 2')

    # =========================================================
    # PRICING
    # =========================================================

    quantity = fields.Integer(
        string='Ordered Qty',
        default=1,
        required=True
    )

    price_unit = fields.Float(
        string='Unit Cost (TSh)',
        required=True,
        default=0.0
    )

    subtotal = fields.Float(
        string='Subtotal (TSh)',
        compute='_compute_subtotal',
        store=True
    )

    # =========================================================
    # RECEIVE TRACKING
    # =========================================================

    qty_received = fields.Integer(
        string='Received Qty',
        default=0,
        readonly=True,
        copy=False
    )

    qty_pending = fields.Integer(
        string='Pending Qty',
        compute='_compute_qty_pending',
        store=True
    )

    receive_status = fields.Selection(
        [
            ('pending', 'Pending'),
            ('partial', 'Partial'),
            ('done', 'Done'),
        ],
        string='Receive Status',
        compute='_compute_receive_status',
        store=True
    )

    # =========================================================
    # COMPUTE: SUBTOTAL
    # =========================================================

    @api.depends('price_unit', 'quantity')
    def _compute_subtotal(self):
        for record in self:
            record.subtotal = (record.price_unit or 0.0) * (record.quantity or 0)

    # =========================================================
    # COMPUTE: QTY PENDING
    # =========================================================

    @api.depends('quantity', 'qty_received')
    def _compute_qty_pending(self):
        for record in self:
            record.qty_pending = max(
                (record.quantity or 0) - (record.qty_received or 0),
                0
            )

    # =========================================================
    # COMPUTE: RECEIVE STATUS
    # =========================================================

    @api.depends('quantity', 'qty_received', 'qty_pending')
    def _compute_receive_status(self):
        for record in self:
            if record.qty_received == 0:
                record.receive_status = 'pending'
            elif record.qty_pending == 0:
                record.receive_status = 'done'
            else:
                record.receive_status = 'partial'

    # =========================================================
    # ONCHANGE: PHONE_ID → jaza fields nyingine
    # =========================================================

    @api.onchange('phone_id')
    def _onchange_phone_id(self):
        for record in self:
            if record.phone_id:
                record.phone_model = record.phone_id.model_name or ""
                record.brand_id = record.phone_id.brand_id
                record.category_id = record.phone_id.category_id
                record.condition_id = record.phone_id.condition_id
                record.imei_1 = record.phone_id.imei_1 or ""
                record.imei_2 = record.phone_id.imei_2 or ""
                record.price_unit = record.phone_id.buying_price or 0.0

    # =========================================================
    # CREATE — TRIGGER PARENT RECOMPUTE
    # =========================================================

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)

        orders = lines.mapped('order_id')
        for order in orders:
            order._compute_totals()
            order._compute_balance()
            order._compute_receive_totals()

        return lines

    # =========================================================
    # WRITE — TRIGGER PARENT RECOMPUTE
    # =========================================================

    def write(self, vals):
        result = super().write(vals)

        orders = self.mapped('order_id')
        for order in orders:
            order._compute_totals()
            order._compute_balance()
            order._compute_receive_totals()

        return result

    # =========================================================
    # UNLINK — TRIGGER PARENT RECOMPUTE
    # =========================================================

    def unlink(self):
        orders = self.mapped('order_id')
        result = super().unlink()

        for order in orders:
            order._compute_totals()
            order._compute_balance()
            order._compute_receive_totals()

        return result