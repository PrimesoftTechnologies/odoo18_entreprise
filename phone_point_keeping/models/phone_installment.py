from odoo import models, fields, api
from datetime import date


class PhoneInstallment(models.Model):
    _name = 'phone.installment'
    _description = 'Phone Debt Installment'
    _rec_name = 'display_name'
    _order = 'debt_id, sequence asc'

    # =========================================================
    # REFERENCE TO DEBT
    # =========================================================

    debt_id = fields.Many2one(
        'phone.debt',
        string='Debt',
        required=True,
        ondelete='cascade'
    )

    sequence = fields.Integer(
        string='#',
        required=True,
        default=1
    )

    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )

    # =========================================================
    # DUE INFO
    # =========================================================

    due_date = fields.Date(
        string='Due Date',
        required=True
    )

    amount = fields.Float(
        string='Amount (TSh)',
        required=True,
        default=0.0
    )

    paid_amount = fields.Float(
        string='Paid Amount (TSh)',
        default=0.0
    )

    balance = fields.Float(
        string='Balance (TSh)',
        compute='_compute_balance',
        store=True
    )

    # =========================================================
    # PAYMENT DETAILS
    # =========================================================

    payment_date = fields.Date(
        string='Payment Date'
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
    # STATUS
    # =========================================================

    state = fields.Selection(
        [
            ('pending', 'Pending'),
            ('paid', 'Paid'),
            ('overdue', 'Overdue'),
            ('partial', 'Partial'),
        ],
        string='Status',
        default='pending',
        required=True,
        compute='_compute_state',
        store=True,
        readonly=False,
    )

    # =========================================================
    # NOTES
    # =========================================================

    notes = fields.Text(
        string='Notes'
    )

    # =========================================================
    # COMPUTE: DISPLAY NAME
    # =========================================================

    @api.depends('debt_id.name', 'sequence')
    def _compute_display_name(self):
        for record in self:
            if record.debt_id and record.debt_id.name:
                record.display_name = f"{record.debt_id.name} - #{record.sequence}"
            else:
                record.display_name = f"#{record.sequence}"

    # =========================================================
    # COMPUTE: BALANCE
    # =========================================================

    @api.depends('amount', 'paid_amount')
    def _compute_balance(self):
        for record in self:
            record.balance = max(
                (record.amount or 0.0) - (record.paid_amount or 0.0),
                0.0
            )

    # =========================================================
    # COMPUTE: STATE (RECURSION-SAFE)
    # =========================================================

    @api.depends('amount', 'paid_amount', 'due_date')
    def _compute_state(self):
        for record in self:
            if record.state == 'paid' and record.paid_amount < record.amount:
                # Reset if unpaid
                pass

            if record.amount <= 0:
                record.state = 'pending'
            elif record.paid_amount >= record.amount:
                record.state = 'paid'
            elif record.paid_amount > 0:
                record.state = 'partial'
            elif record.due_date and record.due_date < date.today():
                record.state = 'overdue'
            else:
                record.state = 'pending'

    # =========================================================
    # ACTIONS
    # =========================================================

    def action_mark_paid(self):
        for record in self:
            record.write({
                'paid_amount': record.amount,
                'payment_date': fields.Date.today(),
            })

    def action_mark_pending(self):
        for record in self:
            record.write({
                'paid_amount': 0.0,
                'payment_date': False,
            })