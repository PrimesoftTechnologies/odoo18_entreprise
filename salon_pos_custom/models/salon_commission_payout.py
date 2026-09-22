from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import timedelta, date


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
                record.gross_commission = sum(lines.mapped("commission_amount"))

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
                    record.gross_commission = sum(lines.mapped("commission_amount"))

                record.advance_deduction = 0.0
            else:
                record.gross_commission = 0.0
                record.advance_deduction = 0.0

            record.net_commission = record.gross_commission - record.advance_deduction

    @api.depends("gross_commission", "advance_deduction")
    def _compute_net_commission(self):
        for record in self:
            record.net_commission = record.gross_commission - record.advance_deduction

    @api.model
    def create(self, vals):
        if vals.get("name", "New") == "New":
            vals["name"] = self.env["ir.sequence"].next_by_code("salon.commission.payout") or "New"
        return super().create(vals)

    def action_mark_paid(self):
        for record in self:
            if record.state != "draft":
                continue
            if record.net_commission < 0:
                raise ValidationError("Net Commission cannot be negative.")
            record.write({"state": "paid"})

    def action_cancel(self):
        for record in self:
            if record.state != "paid":
                raise ValidationError("Only Paid payouts can be cancelled.")
            record.write({"state": "cancelled"})

    def unlink(self):
        for record in self:
            if record.state == "paid":
                raise ValidationError("You cannot delete a Paid Commission Payout.")
        return super().unlink()


class SalonDailyExpenseLine(models.Model):
    _name = "salon.daily.expense.line"
    _description = "Daily Expense Line"

    summary_id = fields.Many2one("salon.pos.report.summary", string="Summary Reference", ondelete="cascade")
    name = fields.Char(string="Description", required=True)
    total_expense = fields.Monetary(string="Expense Amount", required=True)
    currency_id = fields.Many2one("res.currency", related="summary_id.currency_id", store=True)


class SalonPosReportSummary(models.Model):
    _name = "salon.pos.report.summary"
    _description = "POS Sales and Expense Summary"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string="Reference", default=lambda self: "Daily Summary", tracking=True)
    date = fields.Date(string="Date", default=fields.Date.context_today, required=True, tracking=True)
    user_id = fields.Many2one("res.users", string="Cashier", default=lambda self: self.env.user, required=True, tracking=True)
    
    # POS Shop / Register is now optional (required=False)
    config_id = fields.Many2one("pos.config", string="POS Shop / Register", required=False, tracking=True,
                                help="Leave empty to calculate for all shops combined, or select a specific shop.")

    expense_line_ids = fields.One2many("salon.daily.expense.line", "summary_id", string="Daily Expenses")

    opening_cash = fields.Monetary(string="Opening Cash", compute="_compute_net_cash", store=True, currency_field="currency_id")
    gross_sales = fields.Monetary(string="Gross Sales", compute="_compute_net_cash", store=True, currency_field="currency_id")
    total_expenses = fields.Monetary(string="Total Expenses", compute="_compute_net_cash", store=True, currency_field="currency_id")
    net_cash_in_hand = fields.Monetary(string="Net Cash in Hand", compute="_compute_net_cash", store=True, currency_field="currency_id")
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.company.currency_id)
    
    state = fields.Selection([
        ('draft', 'Open'),
        ('closed', 'Closed')
    ], string="Status", default='draft', tracking=True)

    @api.depends("date", "config_id", "expense_line_ids.total_expense")
    def _compute_net_cash(self):
        for record in self:
            if not record.date:
                record.opening_cash = 0.0
                record.gross_sales = 0.0
                record.total_expenses = 0.0
                record.net_cash_in_hand = 0.0
                continue

            # Base domain for previous summary lookup
            domain = [
                ("date", "<", record.date),
            ]
            if record.config_id:
                domain.append(("config_id", "=", record.config_id.id))
            else:
                domain.append(("config_id", "=", False))

            if record.id and not isinstance(record.id, models.NewId):
                domain.append(("id", "!=", record.id))

            last_summary = self.env["salon.pos.report.summary"].search(domain, order="date desc, id desc", limit=1)
            opening = last_summary.net_cash_in_hand if last_summary else 0.0

            # Base domain for POS orders
            pos_domain = [
                ("date_order", ">=", str(record.date) + " 00:00:00"),
                ("date_order", "<=", str(record.date) + " 23:59:59"),
                ("state", "in", ["paid", "done", "invoiced"])
            ]
            if record.config_id:
                pos_domain.append(("config_id", "=", record.config_id.id))

            pos_orders = self.env["pos.order"].search(pos_domain)
            gross = sum(pos_orders.mapped("amount_total"))

            exp_total = sum(record.expense_line_ids.mapped("total_expense"))

            record.opening_cash = opening
            record.gross_sales = gross
            record.total_expenses = exp_total
            record.net_cash_in_hand = (opening + gross) - exp_total

    def action_close_expense(self):
        """Closes today's summary and creates the next day's record for the same shop configuration (or all shops)"""
        self.ensure_one()
        self.write({'state': 'closed'})
        
        next_date = self.date + timedelta(days=1) if self.date else fields.Date.today()
        
        search_domain = [
            ('date', '=', next_date)
        ]
        if self.config_id:
            search_domain.append(('config_id', '=', self.config_id.id))
        else:
            search_domain.append(('config_id', '=', False))

        existing_next = self.env['salon.pos.report.summary'].search(search_domain, limit=1)

        if existing_next:
            action = self.env["ir.actions.actions"]._for_xml_id("salon_pos_custom.action_salon_pos_summary")
            action['res_id'] = existing_next.id
            action['views'] = [(False, 'form')]
            return action

        new_summary = self.env['salon.pos.report.summary'].create({
            'date': next_date,
            'config_id': self.config_id.id if self.config_id else False,
            'user_id': self.user_id.id,
        })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Sales & Expense Summary',
            'res_model': 'salon.pos.report.summary',
            'res_id': new_summary.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_print_summary_report(self):
        self.ensure_one()
        return self.env.ref('salon_pos_custom.action_report_salon_pos_summary').report_action(self)