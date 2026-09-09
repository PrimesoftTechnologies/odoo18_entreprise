from odoo import models, fields, api


class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    employee_id = fields.Many2one(
        "hr.employee",
        string="Employee",
        index=True,
    )

    employee_name = fields.Char(
        string="Employee Name",
        related="employee_id.name",
        store=True,
        index=True,
    )

    is_not_commission = fields.Boolean(
        string="Not Commission",
        related="product_id.product_tmpl_id.is_not_commission",
        store=True,
        index=True,
    )

    is_fixed_commission = fields.Boolean(
        string="Fixed Commission",
        related="product_id.product_tmpl_id.is_fixed_commission",
        store=True,
        index=True,
    )

    fixed_commission_amount = fields.Monetary(
        string="Fixed Commission Amount",
        currency_field="currency_id",
        related="product_id.product_tmpl_id.fixed_commission_amount",
        store=True,
        index=True,
    )

    commission_amount = fields.Monetary(
        string="Commission",
        currency_field="currency_id",
        compute="_compute_commission_amount",
        store=True,
        index=True,
    )

    commission_date = fields.Datetime(
        string="Order Date",
        related="order_id.date_order",
        store=True,
        index=True,
    )

    commission_order_id = fields.Many2one(
        "pos.order",
        string="Order",
        related="order_id",
        store=True,
        index=True,
    )

    pos_config_id = fields.Many2one(
        "pos.config",
        string="Point of Sale",
        related="order_id.session_id.config_id",
        store=True,
        index=True,
        readonly=True,
    )

    @api.depends(
        "price_unit",
        "qty",
        "employee_id",
        "product_id",
        "product_id.product_tmpl_id.is_not_commission",
        "product_id.product_tmpl_id.is_fixed_commission",
        "product_id.product_tmpl_id.fixed_commission_amount",
    )
    def _compute_commission_amount(self):

        for line in self:

            # 1. Kama hakuna employee, commission inakuwa 0.0
            if not line.employee_id:
                line.commission_amount = 0.0
                continue

            # 2. Kama bidhaa imetiwa alama ya 'Not Commission', commission inakuwa 0.0
            if line.product_id and line.product_id.product_tmpl_id.is_not_commission:
                line.commission_amount = 0.0
                continue

            qty = line.qty or 0.0

            # 3. Kama bidhaa ina 'Fixed Commission', tumia kiasi hicho maalum mara idadi (qty)
            if line.product_id and line.product_id.product_tmpl_id.is_fixed_commission:
                line.commission_amount = (line.fixed_commission_amount or 0.0) * qty
                continue

            # 4. KAMA ZOTE ZIKIWA HAZIJACHAGULIWA (HAKUNA TICK):
            # Tumia ile mantiki ya asilimia (Brackets) ya kawaida!
            service_price = line.price_unit or 0.0
            commission_per_service = 0.0

            if 5000 <= service_price <= 20000:
                commission_per_service = service_price * 0.30

            elif 25000 <= service_price <= 45000:
                commission_per_service = 20000 * 0.30

            elif service_price >= 50000:
                commission_per_service = 40000 * 0.30

            line.commission_amount = (
                commission_per_service * qty
            )

    def _order_line_fields(
        self,
        line,
        session_id=None,
    ):

        vals = super()._order_line_fields(
            line,
            session_id,
        )

        if line.get("employee_id"):
            vals[2]["employee_id"] = line["employee_id"]

        return vals