from odoo import fields, models


# ============================================================
# SALE ORDER EXTENSION
# ============================================================

class SaleOrder(models.Model):
    _inherit = "sale.order"

    van_route_id = fields.Many2one(
        "van.route",
        string="Sales Route",
        index=True,
        copy=False,
    )

    van_salesman_id = fields.Many2one(
        "res.users",
        string="Van Salesman",
        index=True,
        copy=False,
    )


# ============================================================
# SALES BY ROUTE
# ============================================================

class VanSalesByRoute(models.Model):
    _name = "van.sales.by.route"
    _description = "Van Sales by Route"
    _auto = False
    _rec_name = "route_id"
    _order = "route_id"

    route_id = fields.Many2one(
        "van.route",
        string="Route",
        readonly=True,
    )

    van_id = fields.Many2one(
        "fleet.vehicle",
        string="Van",
        readonly=True,
    )

    salesman_id = fields.Many2one(
        "res.users",
        string="Salesman",
        readonly=True,
    )

    customer_count = fields.Integer(
        string="Customers",
        readonly=True,
    )

    order_count = fields.Integer(
        string="Sales Orders",
        readonly=True,
    )

    total_amount = fields.Monetary(
        string="Total Sales",
        readonly=True,
        currency_field="currency_id",
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        readonly=True,
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        readonly=True,
    )

    def init(self):
        self.env.cr.execute("""
            DROP VIEW IF EXISTS van_sales_by_route CASCADE
        """)

        self.env.cr.execute("""
            CREATE VIEW van_sales_by_route AS (

                SELECT

                    vr.id AS id,

                    vr.id AS route_id,

                    vr.van_id AS van_id,

                    vr.salesman_id AS salesman_id,

                    COUNT(
                        DISTINCT so.partner_id
                    ) FILTER (
                        WHERE so.state IN ('sale', 'done')
                    ) AS customer_count,

                    COUNT(
                        DISTINCT so.id
                    ) FILTER (
                        WHERE so.state IN ('sale', 'done')
                    ) AS order_count,

                    COALESCE(
                        SUM(
                            CASE
                                WHEN so.state IN ('sale', 'done')
                                THEN so.amount_total
                                ELSE 0
                            END
                        ),
                        0
                    ) AS total_amount,

                    company.currency_id AS currency_id,

                    vr.company_id AS company_id

                FROM van_route vr

                LEFT JOIN sale_order so
                    ON so.van_route_id = vr.id

                LEFT JOIN res_company company
                    ON company.id = vr.company_id

                GROUP BY
                    vr.id,
                    vr.van_id,
                    vr.salesman_id,
                    vr.company_id,
                    company.currency_id
            )
        """)


# ============================================================
# SALES BY SALESMAN
# ============================================================

class VanSalesBySalesman(models.Model):
    _name = "van.sales.by.salesman"
    _description = "Van Sales by Salesman"
    _auto = False
    _rec_name = "salesman_id"
    _order = "total_amount desc"

    salesman_id = fields.Many2one(
        "res.users",
        string="Salesman",
        readonly=True,
    )

    route_count = fields.Integer(
        string="Routes",
        readonly=True,
    )

    customer_count = fields.Integer(
        string="Customers",
        readonly=True,
    )

    order_count = fields.Integer(
        string="Sales Orders",
        readonly=True,
    )

    total_amount = fields.Monetary(
        string="Total Sales",
        readonly=True,
        currency_field="currency_id",
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        readonly=True,
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        readonly=True,
    )

    def init(self):
        self.env.cr.execute("""
            DROP VIEW IF EXISTS van_sales_by_salesman CASCADE
        """)

        self.env.cr.execute("""
            CREATE VIEW van_sales_by_salesman AS (

                SELECT

                    ROW_NUMBER() OVER (
                        ORDER BY
                            so.van_salesman_id,
                            so.company_id
                    ) AS id,

                    so.van_salesman_id AS salesman_id,

                    COUNT(
                        DISTINCT so.van_route_id
                    ) FILTER (
                        WHERE so.state IN ('sale', 'done')
                    ) AS route_count,

                    COUNT(
                        DISTINCT so.partner_id
                    ) FILTER (
                        WHERE so.state IN ('sale', 'done')
                    ) AS customer_count,

                    COUNT(
                        DISTINCT so.id
                    ) FILTER (
                        WHERE so.state IN ('sale', 'done')
                    ) AS order_count,

                    COALESCE(
                        SUM(
                            CASE
                                WHEN so.state IN ('sale', 'done')
                                THEN so.amount_total
                                ELSE 0
                            END
                        ),
                        0
                    ) AS total_amount,

                    company.currency_id AS currency_id,

                    so.company_id AS company_id

                FROM sale_order so

                LEFT JOIN res_company company
                    ON company.id = so.company_id

                WHERE so.van_salesman_id IS NOT NULL

                GROUP BY
                    so.van_salesman_id,
                    so.company_id,
                    company.currency_id
            )
        """)


# ============================================================
# SALES REPORT
# ============================================================

class VanSalesReport(models.Model):
    _name = "van.sales.report"
    _description = "Van Sales Report"
    _auto = False
    _rec_name = "order_name"
    _order = "date_order desc"

    date_order = fields.Datetime(
        string="Order Date",
        readonly=True,
    )

    order_id = fields.Many2one(
        "sale.order",
        string="Sales Order",
        readonly=True,
    )

    order_name = fields.Char(
        string="Order Number",
        readonly=True,
    )

    customer_id = fields.Many2one(
        "res.partner",
        string="Customer",
        readonly=True,
    )

    salesman_id = fields.Many2one(
        "res.users",
        string="Salesman",
        readonly=True,
    )

    route_id = fields.Many2one(
        "van.route",
        string="Sales Route",
        readonly=True,
    )

    van_id = fields.Many2one(
        "fleet.vehicle",
        string="Van",
        readonly=True,
    )

    amount_untaxed = fields.Monetary(
        string="Untaxed Amount",
        readonly=True,
        currency_field="currency_id",
    )

    amount_tax = fields.Monetary(
        string="Tax",
        readonly=True,
        currency_field="currency_id",
    )

    amount_total = fields.Monetary(
        string="Total",
        readonly=True,
        currency_field="currency_id",
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        readonly=True,
    )

    state = fields.Selection(
        [
            ("draft", "Quotation"),
            ("sent", "Quotation Sent"),
            ("sale", "Sales Order"),
            ("done", "Locked"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        readonly=True,
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        readonly=True,
    )

    def init(self):
        self.env.cr.execute("""
            DROP VIEW IF EXISTS van_sales_report CASCADE
        """)

        self.env.cr.execute("""
            CREATE VIEW van_sales_report AS (

                SELECT

                    so.id AS id,

                    so.date_order AS date_order,

                    so.id AS order_id,

                    so.name AS order_name,

                    so.partner_id AS customer_id,

                    so.van_salesman_id AS salesman_id,

                    so.van_route_id AS route_id,

                    vr.van_id AS van_id,

                    so.amount_untaxed AS amount_untaxed,

                    so.amount_tax AS amount_tax,

                    so.amount_total AS amount_total,

                    so.currency_id AS currency_id,

                    so.state AS state,

                    so.company_id AS company_id

                FROM sale_order so

                LEFT JOIN van_route vr
                    ON vr.id = so.van_route_id
            )
        """)