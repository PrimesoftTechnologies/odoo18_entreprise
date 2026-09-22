from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import timedelta


class SalonCommissionPayout(models.Model):
    _name = "salon.commission.payout"
    _description = "Employee Commission Payout & Deductions"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(
        string="Reference",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: "New"
    )

    employee_id = fields.Many2one(
        "hr.employee",
        string="Employee",
        required=True,
        tracking=True
    )

    date = fields.Date(
        string="Date",
        required=True,
        default=fields.Date.context_today,
        tracking=True
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id
    )

    gross_commission = fields.Monetary(
        string="Gross Commission",
        compute="_compute_gross_commission",
        store=True,
        readonly=False,
        currency_field="currency_id"
    )

    advance_deduction = fields.Monetary(
        string="Deductions / Advances Taken",
        currency_field="currency_id",
        tracking=True,
        help="Amount taken in advance or deductions to subtract from total commission."
    )

    net_commission = fields.Monetary(
        string="Net Commission to Pay",
        compute="_compute_net_commission",
        store=True,
        currency_field="currency_id",
        tracking=True
    )

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("paid", "Paid"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="draft",
        tracking=True
    )

    # =========================================================
    # GROSS COMMISSION
    # =========================================================

    @api.depends("employee_id", "date")
    def _compute_gross_commission(self):
        for record in self:

            if not record.employee_id:
                record.gross_commission = 0.0
                continue

            domain = [
                ("employee_id", "=", record.employee_id.id),
                ("state", "=", "paid"),
            ]

            if record.id and not isinstance(record.id, models.NewId):
                domain.append(("id", "!=", record.id))

            last_payout = self.env["salon.commission.payout"].search(
                domain,
                order="id desc",
                limit=1
            )

            if last_payout:
                record.gross_commission = last_payout.net_commission
            else:
                pos_domain = [
                    ("employee_id", "=", record.employee_id.id),
                    ("commission_amount", ">", 0)
                ]

                if record.date:
                    date_datetime = fields.Datetime.to_datetime(record.date) + timedelta(days=1)
                    pos_domain.append(("order_id.date_order", "<", date_datetime))

                lines = self.env["pos.order.line"].search(pos_domain)

                record.gross_commission = sum(
                    lines.mapped("commission_amount")
                )

    # =========================================================
    # ONCHANGE EMPLOYEE OR DATE
    # =========================================================

    @api.onchange("employee_id", "date")
    def _onchange_employee_date(self):
        for record in self:

            if record.employee_id:

                domain = [
                    ("employee_id", "=", record.employee_id.id),
                    ("state", "=", "paid"),
                ]

                origin_id = record._origin.id

                if origin_id and not isinstance(origin_id, models.NewId):
                    domain.append(("id", "!=", origin_id))

                last_payout = self.env["salon.commission.payout"].search(
                    domain,
                    order="id desc",
                    limit=1
                )

                if last_payout:
                    record.gross_commission = last_payout.net_commission
                else:
                    pos_domain = [
                        ("employee_id", "=", record.employee_id.id),
                        ("commission_amount", ">", 0)
                    ]

                    if record.date:
                        date_datetime = fields.Datetime.to_datetime(record.date) + timedelta(days=1)
                        pos_domain.append(("order_id.date_order", "<", date_datetime))

                    lines = self.env["pos.order.line"].search(pos_domain)

                    record.gross_commission = sum(
                        lines.mapped("commission_amount")
                    )

                record.advance_deduction = 0.0

            else:
                record.gross_commission = 0.0
                record.advance_deduction = 0.0

            record.net_commission = (
                record.gross_commission
                - record.advance_deduction
            )

    # =========================================================
    # NET COMMISSION
    # =========================================================

    @api.depends(
        "gross_commission",
        "advance_deduction"
    )
    def _compute_net_commission(self):
        for record in self:
            record.net_commission = (
                record.gross_commission
                - record.advance_deduction
            )

    # =========================================================
    # CREATE / SEQUENCE
    # =========================================================

    @api.model
    def create(self, vals):
        if vals.get("name", "New") == "New":
            vals["name"] = (
                self.env["ir.sequence"].next_by_code(
                    "salon.commission.payout"
                )
                or "New"
            )
        return super().create(vals)

    # =========================================================
    # MARK AS PAID
    # =========================================================

    def action_mark_paid(self):
        for record in self:
            if record.state != "draft":
                continue
            if record.net_commission < 0:
                raise ValidationError(
                    "Net Commission cannot be negative."
                )
            record.write({
                "state": "paid"
            })

    # =========================================================
    # CANCEL PAYOUT
    # =========================================================

    def action_cancel(self):
        for record in self:
            if record.state != "paid":
                raise ValidationError(
                    "Only Paid payouts can be cancelled."
                )
            record.write({
                "state": "cancelled"
            })

    # =========================================================
    # PREVENT DELETE OF PAID PAYOUTS
    # =========================================================

    def unlink(self):
        for record in self:
            if record.state == "paid":
                raise ValidationError(
                    "You cannot delete a Paid Commission Payout.\n\n"
                    "Paid payouts are part of the commission payment history. "
                    "If this payout was entered by mistake, use Cancelled "
                    "instead of deleting it."
                )
        return super().unlink()


class SalonDailyExpense(models.Model):
    _name = "salon.daily.expense"
    _description = "Daily Expense POS"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(
        string="Description",
        required=True,
        tracking=True,
        help="Description or reason for the expense."
    )

    total_expense = fields.Monetary(
        string="Total Expense",
        required=True,
        currency_field="currency_id",
        tracking=True
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id
    )

    user_id = fields.Many2one(
        "res.users",
        string="Employee (Cashier)",
        required=True,
        default=lambda self: self.env.user,
        tracking=True
    )

    date = fields.Date(
        string="Date",
        required=True,
        default=fields.Date.context_today,
        tracking=True
    )


class SalonPosReportSummary(models.Model):
    _name = "salon.pos.report.summary"
    _description = "POS Sales and Expense Summary"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string="Reference", default=lambda self: "Daily Summary")
    date = fields.Date(string="Date", default=fields.Date.context_today, required=True)
    user_id = fields.Many2one("res.users", string="Cashier", default=lambda self: self.env.user, required=True)
    
    gross_sales = fields.Monetary(string="Gross Sales (Mauzo)", compute="_compute_net_cash", store=True)
    total_expenses = fields.Monetary(string="Total Expenses (Matumizi)", compute="_compute_net_cash", store=True)
    net_cash_in_hand = fields.Monetary(string="Net Cash (Pesa Halisi)", compute="_compute_net_cash", store=True)
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.company.currency_id)

    @api.depends("date", "user_id")
    def _compute_net_cash(self):
        for record in self:
            if not record.date or not record.user_id:
                record.gross_sales = 0.0
                record.total_expenses = 0.0
                record.net_cash_in_hand = 0.0
                continue

            # 1. Pata jumla ya mauzo ya POS kwa tarehe na mtumiaji/cashier huyo
            pos_orders = self.env["pos.order"].search([
                ("user_id", "=", record.user_id.id),
                ("date_order", ">=", str(record.date) + " 00:00:00"),
                ("date_order", "<=", str(record.date) + " 23:59:59"),
                ("state", "in", ["paid", "done", "invoiced"])
            ])
            gross = sum(pos_orders.mapped("amount_total"))

            # 2. Pata jumla ya matumizi ya siku hiyo kwa mtumiaji huyo
            expenses = self.env["salon.daily.expense"].search([
                ("user_id", "=", record.user_id.id),
                ("date", "=", record.date)
            ])
            exp_total = sum(expenses.mapped("total_expense"))

            # 3. Hesabu mauzo halisi ukiondoa matumizi
            record.gross_sales = gross
            record.total_expenses = exp_total
            record.net_cash_in_hand = gross - exp_total