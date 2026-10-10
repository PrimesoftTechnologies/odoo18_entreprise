from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class PhoneSaleOrder(models.Model):
    _name = 'phone.sale.order'
    _description = 'Phone Sale Order (POS)'
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
        string='Customer'
    )

    customer_phone = fields.Char(
        string='Customer Phone'
    )

    # =========================================================
    # DATE
    # =========================================================

    date = fields.Datetime(
        string='Sale Date',
        default=fields.Datetime.now,
        required=True
    )

    # =========================================================
    # PAYMENT
    # =========================================================

    payment_type = fields.Selection(
        [
            ('cash', 'Cash'),
            ('credit', 'Credit'),
        ],
        string='Payment Type',
        default='cash',
        required=True
    )

    payment_method = fields.Selection(
        [
            ('cash', 'Cash (Physical)'),
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
            ('draft', 'Draft'),
            ('paid', 'Paid'),
            ('partial', 'Partial'),
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
        'phone.sale.order.line',
        'order_id',
        string='Sale Lines'
    )

    line_count = fields.Integer(
        string='Lines Count',
        compute='_compute_totals',
        store=True
    )

    # =========================================================
    # TOTALS (computed)
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

    total_profit = fields.Float(
        string='Total Profit (TSh)',
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
    # NOTES
    # =========================================================

    notes = fields.Text(
        string='Notes'
    )

    # =========================================================
    # COMPUTE: TOTALS
    # =========================================================

    @api.depends(
        'line_ids',
        'line_ids.subtotal',
        'line_ids.profit',
        'line_ids.quantity',
        'line_ids.price_unit',
        'line_ids.cost_price',
    )
    def _compute_totals(self):
        for record in self:
            record.line_count = len(record.line_ids)
            record.subtotal = sum(record.line_ids.mapped('subtotal'))
            record.total = record.subtotal
            record.total_profit = sum(record.line_ids.mapped('profit'))

    # =========================================================
    # COMPUTE: BALANCE
    # =========================================================

    @api.depends('total', 'amount_paid')
    def _compute_balance(self):
        for record in self:
            record.balance = max(
                (record.total or 0.0) - (record.amount_paid or 0.0),
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
                    self.env['ir.sequence'].next_by_code('phone.sale.order')
                    or 'New'
                )
        orders = super().create(vals_list)

        # Force recompute in case lines were passed in vals
        for order in orders:
            if order.line_ids:
                order._compute_totals()
                order._compute_balance()

        return orders

    # =========================================================
    # WRITE — FORCE RECOMPUTE WHEN LINES CHANGE
    # =========================================================

    def write(self, vals):
        result = super().write(vals)

        # Force recompute when line_ids change
        if 'line_ids' in vals:
            for record in self:
                record._compute_totals()
                record._compute_balance()

        return result

    # =========================================================
    # ACTIONS
    # =========================================================

    def action_confirm(self):
        """
        Confirm sale — validate stock, reduce quantity, force status refresh.

        MUHIMU: Tunatumia `invalidate_recordset(['quantity', 'status'])` kabla
        ya kusoma `phone.quantity` ili kupata value FRESH kutoka DB, badala ya
        cache ya transaction.
        """

        for record in self:

            # Force recompute before confirming
            record._compute_totals()
            record._compute_balance()

            # =========================================================
            # STEP 1: CHECK KABLA — hakikisha stock inatosha
            # =========================================================
            for line in record.line_ids:
                if line.phone_id:

                    # ✅ Re-read fresh kutoka DB
                    phone = self.env['phone.stock'].browse(line.phone_id.id)
                    phone.invalidate_recordset(['quantity', 'status'])

                    available = phone.quantity or 0
                    needed = line.quantity or 1

                    if needed > available:
                        raise UserError(
                            f"Hakuna stock ya kutosha kwa {phone.model_name}.\n"
                            f"Iliyopo: {available}\n"
                            f"Unataka kuuza: {needed}"
                        )

            # =========================================================
            # STEP 2: PUNGUZA stock quantity kwa kila line
            # =========================================================
            for line in record.line_ids:
                if line.phone_id:

                    # ✅ Re-read fresh kutoka DB kila loop
                    phone = self.env['phone.stock'].browse(line.phone_id.id)
                    phone.invalidate_recordset(['quantity', 'status'])

                    qty_sold = line.quantity or 1
                    old_qty = phone.quantity or 0
                    new_qty = max(old_qty - qty_sold, 0)

                    # ✅ WRITE quantity — status ita-compute yenyewe
                    # (hakuna haja ya kuita _compute_status() manual)
                    phone.write({'quantity': new_qty})

                    # ✅ Re-read tena ili tuone status mpya kwenye log
                    phone.invalidate_recordset(['quantity', 'status'])

                    _logger.info(
                        f"✅ SALE CONFIRMED | {phone.model_name} | "
                        f"Before: {old_qty} | Sold: {qty_sold} | "
                        f"After: {new_qty} | Status: {phone.status}"
                    )

            # =========================================================
            # STEP 3: Set state based on balance
            # =========================================================
            if record.balance <= 0:
                record.state = 'paid'
            else:
                record.state = 'partial'

    def action_cancel(self):
        for record in self:
            record.state = 'cancelled'


class PhoneSaleOrderLine(models.Model):
    _name = 'phone.sale.order.line'
    _description = 'Phone Sale Order Line'
    _rec_name = 'phone_name'
    _order = 'id asc'

    # =========================================================
    # RELATIONSHIP
    # =========================================================

    order_id = fields.Many2one(
        'phone.sale.order',
        string='Sale Order',
        required=True,
        ondelete='cascade'
    )

    phone_id = fields.Many2one(
        'phone.stock',
        string='Phone',
        required=True
    )

    # =========================================================
    # PHONE INFO (related)
    # =========================================================

    phone_name = fields.Char(
        string='Phone Name',
        related='phone_id.model_name',
        store=True
    )

    phone_brand = fields.Char(
        string='Brand',
        related='phone_id.brand_id.name',
        store=True
    )

    imei_1 = fields.Char(
        string='IMEI 1',
        related='phone_id.imei_1',
        store=True
    )

    # =========================================================
    # PRICING
    # =========================================================

    price_unit = fields.Float(
        string='Unit Price (TSh)',
        required=True,
        default=0.0
    )

    cost_price = fields.Float(
        string='Cost Price (TSh)',
        default=0.0
    )

    quantity = fields.Integer(
        string='Quantity',
        default=1,
        required=True
    )

    subtotal = fields.Float(
        string='Subtotal (TSh)',
        compute='_compute_subtotal',
        store=True
    )

    profit = fields.Float(
        string='Profit (TSh)',
        compute='_compute_profit',
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
    # COMPUTE: PROFIT
    # =========================================================

    @api.depends('price_unit', 'cost_price', 'quantity')
    def _compute_profit(self):
        for record in self:
            record.profit = (
                (record.price_unit or 0.0) - (record.cost_price or 0.0)
            ) * (record.quantity or 0)

    # =========================================================
    # CREATE — TRIGGER PARENT RECOMPUTE
    # =========================================================

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)

        # Trigger parent order recompute
        orders = lines.mapped('order_id')
        for order in orders:
            order._compute_totals()
            order._compute_balance()

        return lines

    # =========================================================
    # WRITE — TRIGGER PARENT RECOMPUTE
    # =========================================================

    def write(self, vals):
        result = super().write(vals)

        # Trigger parent order recompute
        orders = self.mapped('order_id')
        for order in orders:
            order._compute_totals()
            order._compute_balance()

        return result

    # =========================================================
    # UNLINK — TRIGGER PARENT RECOMPUTE
    # =========================================================

    def unlink(self):
        # Save orders BEFORE unlink
        orders = self.mapped('order_id')

        result = super().unlink()

        # Recompute orders AFTER unlink
        for order in orders:
            order._compute_totals()
            order._compute_balance()

        return result