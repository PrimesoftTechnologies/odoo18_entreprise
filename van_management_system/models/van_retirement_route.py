# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class VanRetirementRoute(models.Model):
    _name = "van.retirement.route"
    _description = "Van Route Retirement"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "route_date desc, id desc"

    name = fields.Char(
        string="Retirement Reference",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
        tracking=True,
    )

    pos_session_ref = fields.Char(
        string="POS ID / Session",
        tracking=True,
    )

    route_id = fields.Many2one(
        "van.route",
        string="Sales Route",
        required=True,
        readonly=True,
        tracking=True,
        index=True,
        ondelete="restrict",
    )

    route_number = fields.Char(
        string="Route Number",
        compute="_compute_route_information",
        store=True,
        readonly=True,
    )

    route_name = fields.Char(
        string="Route Start to End",
        compute="_compute_route_information",
        store=True,
        readonly=True,
    )

    route_description = fields.Text(
        string="Route Description",
        compute="_compute_route_information",
        store=True,
        readonly=True,
    )

    route_state = fields.Selection([
        ("draft", "Draft"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ], string="Route Status", compute="_compute_route_information", store=True, readonly=True, default="draft")

    route_date = fields.Date(
        string="Route Date",
        compute="_compute_route_information",
        store=True,
        readonly=True,
        tracking=True,
    )

    van_id = fields.Many2one(
        "fleet.vehicle",
        string="Van",
        compute="_compute_route_information",
        store=True,
        readonly=True,
    )

    salesman_id = fields.Many2one(
        "res.users",
        string="Salesman",
        compute="_compute_route_information",
        store=True,
        readonly=True,
    )

    supervisor_id = fields.Many2one(
        "res.users",
        string="Supervisor",
        compute="_compute_route_information",
        store=True,
        readonly=True,
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        tracking=True,
    )

    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        store=True,
        readonly=True,
    )

    # ==========================================================
    # SALES SUMMARY
    # ==========================================================

    total_expected_sales = fields.Monetary(
        string="Total Expected Sales",
        compute="_compute_sales_totals",
        store=True,
        currency_field="currency_id",
        tracking=True,
    )

    total_actual_sales = fields.Monetary(
        string="Total Actual Sales",
        compute="_compute_sales_totals",
        store=True,
        currency_field="currency_id",
        tracking=True,
    )

    sales_variance = fields.Monetary(
        string="Sales Variance",
        compute="_compute_sales_totals",
        store=True,
        currency_field="currency_id",
    )

    # PAYMENT METHOD SUMMARY FIELD
    payment_method_summary = fields.Text(
        string="Payment Methods Summary",
        compute="_compute_payment_method_summary",
        store=True,
    )

    product_line_ids = fields.One2many(
        "van.retirement.route.line",
        "retirement_id",
        string="Products",
        copy=True,
    )

    stop_line_ids = fields.One2many(
        "van.retirement.route.stop",
        "retirement_id",
        string="Route Stops",
        copy=True,
    )

    stock_picking_id = fields.Many2one(
        "stock.picking",
        string="Stock Return Transfer",
        readonly=True,
        copy=False,
    )
    picking_count = fields.Integer(
        string="Picking Count",
        compute="_compute_picking_count",
    )

    requested_by = fields.Many2one(
        "res.users",
        string="Requested By",
        default=lambda self: self.env.user,
        readonly=True,
        tracking=True,
    )

    approved_by = fields.Many2one(
        "res.users",
        string="Approved By",
        readonly=True,
        tracking=True,
    )

    approved_date = fields.Datetime(
        string="Approved Date",
        readonly=True,
    )

    completed_date = fields.Datetime(
        string="Completed Date",
        readonly=True,
    )

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("approved", "Approved"),
            ("done", "Done"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="draft",
        required=True,
        tracking=True,
        index=True,
    )

    note = fields.Text(string="Notes")

    # ==========================================================
    # UNIQUE POS SESSION CONSTRAINT (Huzuia kurudia kutumia POS ID)
    # ==========================================================
    @api.constrains('pos_session_ref')
    def _check_unique_pos_session(self):
        for record in self:
            if record.pos_session_ref:
                existing = self.search([
                    ('pos_session_ref', '=', record.pos_session_ref.strip()),
                    ('id', '!=', record.id),
                    ('state', 'in', ('submitted', 'approved', 'done'))
                ], limit=1)
                if existing:
                    raise ValidationError(_(
                        f"POS ID / Session '{record.pos_session_ref}' Sorry! This POS ID already used in previously retirement "
                        f"Retirement nyingine (Ref: {existing.name}). Not allowed to repeat this id!"
                    ))

    @api.depends("pos_session_ref")
    def _compute_payment_method_summary(self):
        for record in self:
            summary_text = ""
            if record.pos_session_ref:
                session = self.env['pos.session'].search([('name', '=', record.pos_session_ref)], limit=1)
                if session:
                    orders = self.env['pos.order'].search([('session_id', '=', session.id)])
                    payments = self.env['pos.payment'].search([('pos_order_id', 'in', orders.ids)])
                    
                    payment_totals = {}
                    for pay in payments:
                        method_name = pay.payment_method_id.name or _("Unknown")
                        payment_totals[method_name] = payment_totals.get(method_name, 0.0) + pay.amount
                    
                    lines = []
                    for method, amount in payment_totals.items():
                        lines.append(f"{method}: {amount:,.2f}")
                    
                    summary_text = "\n".join(lines) if lines else _("No payments recorded.")
            record.payment_method_summary = summary_text

    @api.depends("stock_picking_id")
    def _compute_picking_count(self):
        for record in self:
            record.picking_count = 1 if record.stock_picking_id else 0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals.get("name") == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code("van.retirement.route") or _("New")
            if not vals.get("company_id"):
                vals["company_id"] = self.env.company.id
            if not vals.get("requested_by"):
                vals["requested_by"] = self.env.user.id

        records = super().create(vals_list)
        for record in records:
            record._create_product_lines_from_route()
        return records

    @api.depends("route_id")
    def _compute_route_information(self):
        for record in self:
            route = record.route_id
            record.route_number = False
            record.route_name = False
            record.route_description = False
            record.route_state = "draft"
            record.van_id = False
            record.salesman_id = False
            record.supervisor_id = False
            record.route_date = fields.Date.context_today(record)

            if not route:
                continue

            if "route_date" in route._fields and route.route_date:
                record.route_date = route.route_date
            elif "date" in route._fields and route.date:
                record.route_date = route.date

            if "route_number" in route._fields:
                record.route_number = route.route_number
            elif "code" in route._fields:
                record.route_number = route.code
            else:
                record.route_number = route.name

            start_loc = False
            end_loc = False

            if "start_location" in route._fields:
                start_loc = route.start_location
            elif "origin" in route._fields:
                start_loc = route.origin

            if "end_location" in route._fields:
                end_loc = route.end_location
            elif "destination" in route._fields:
                end_loc = route.destination

            if not start_loc and hasattr(route, 'stop_line_ids') and route.stop_line_ids:
                start_loc = route.stop_line_ids[0].stop_name or getattr(route.stop_line_ids[0], 'name', False)
                end_loc = route.stop_line_ids[-1].stop_name or getattr(route.stop_line_ids[-1], 'name', False)

            if not start_loc or not end_loc:
                route_title = route.name or ""
                if " to " in route_title:
                    parts = route_title.split(" to ")
                    start_loc = parts[0].strip()
                    end_loc = parts[1].strip()
                elif " - " in route_title:
                    parts = route_title.split(" - ")
                    start_loc = parts[0].strip()
                    end_loc = parts[1].strip()
                else:
                    start_loc = route_title
                    end_loc = "Destination"

            record.route_name = f"{start_loc} to {end_loc}"

            if "description" in route._fields:
                record.route_description = route.description
            elif "note" in route._fields:
                record.route_description = route.note

            if "state" in route._fields:
                record.route_state = str(route.state) if route.state else "in_progress"

            if "van_id" in route._fields:
                record.van_id = route.van_id

            if "salesman_id" in route._fields:
                record.salesman_id = route.salesman_id

            if "supervisor_id" in route._fields:
                record.supervisor_id = route.supervisor_id

    @api.depends(
        "product_line_ids.expected_revenue",
        "product_line_ids.actual_revenue",
    )
    def _compute_sales_totals(self):
        for record in self:
            expected = sum(record.product_line_ids.mapped("expected_revenue"))
            actual = sum(record.product_line_ids.mapped("actual_revenue"))

            record.total_expected_sales = expected
            record.total_actual_sales = actual
            record.sales_variance = actual - expected

    def _create_product_lines_from_route(self):
        ProductLine = self.env["van.retirement.route.line"]
        for record in self:
            if not record.route_id or record.product_line_ids:
                continue
            route = record.route_id
            if "product_line_ids" not in route._fields:
                continue

            for route_line in route.product_line_ids:
                product = route_line.product_id
                if not product:
                    continue

                expected_quantity = 0.0
                if "expected_quantity" in route_line._fields:
                    expected_quantity = route_line.expected_quantity
                elif "approved_quantity" in route_line._fields:
                    expected_quantity = route_line.approved_quantity
                elif "quantity" in route_line._fields:
                    expected_quantity = route_line.quantity

                sales_price = product.lst_price or 0.0
                if "sales_price" in route_line._fields:
                    sales_price = route_line.sales_price or 0.0

                ProductLine.create({
                    "retirement_id": record.id,
                    "product_id": product.id,
                    "expected_quantity": expected_quantity,
                    "actual_quantity": 0.0,
                    "sales_price": sales_price,
                })

    def action_submit(self):
        for record in self:
            if record.state != "draft":
                raise UserError(_("Only Draft retirement routes can be submitted."))
            if not record.route_id:
                raise ValidationError(_("Please select a Sales Route before submitting."))
            if not record.product_line_ids:
                raise ValidationError(_("The retirement route has no products."))
            
            # Ukaguzi wa ziada wa POS ID wakati wa kubonyeza Submit
            if record.pos_session_ref:
                existing = self.search([
                    ('pos_session_ref', '=', record.pos_session_ref.strip()),
                    ('id', '!=', record.id),
                    ('state', 'in', ('submitted', 'approved', 'done'))
                ], limit=1)
                if existing:
                    raise ValidationError(_(
                        f"POS ID / Session '{record.pos_session_ref}'  Sorry! This POS ID already used in previously record "
                        f"Retirement nyingine (Ref: {existing.name}). Not allowed to submit!"
                    ))

            record.write({
                "state": "submitted",
                "requested_by": self.env.user.id,
            })
        return True

    def action_approve(self):
        for record in self:
            if record.state != "submitted":
                raise UserError(_("Only Submitted retirement routes can be approved."))
            if record.requested_by == self.env.user:
                raise UserError(_("You cannot approve your own retirement route request!"))

            record.write({
                "state": "approved",
                "approved_by": self.env.user.id,
                "approved_date": fields.Datetime.now(),
            })
        return True

    def action_done(self):
        for record in self:
            if record.state != "approved":
                raise UserError(_("Only Approved retirement routes can be completed."))
            
            record._create_stock_return_picking()

            record.write({
                "state": "done",
                "completed_date": fields.Datetime.now(),
            })
        return True

    def _create_stock_return_picking(self):
        self.ensure_one()
        company = self.company_id
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', company.id)], limit=1)
        
        if not warehouse or not warehouse.lot_stock_id or not warehouse.int_type_id:
            return

        dest_location_id = warehouse.lot_stock_id.id
        
        source_location_id = dest_location_id
        if self.van_id:
            van_location = self.env['stock.location'].search([
                ('name', 'ilike', self.van_id.name),
                ('usage', '=', 'internal')
            ], limit=1)
            if van_location:
                source_location_id = van_location.id
            elif hasattr(self.van_id, 'location_id') and self.van_id.location_id:
                source_location_id = self.van_id.location_id.id

        move_lines = []
        for line in self.product_line_ids:
            return_qty = line.expected_quantity - line.actual_quantity
            if return_qty > 0:
                move_lines.append((0, 0, {
                    'name': line.product_id.name,
                    'product_id': line.product_id.id,
                    'product_uom_qty': return_qty,
                    'product_uom': line.product_uom_id.id,
                    'location_id': source_location_id,
                    'location_dest_id': dest_location_id,
                }))

        if move_lines:
            picking_vals = {
                'picking_type_id': warehouse.int_type_id.id,
                'location_id': source_location_id,
                'location_dest_id': dest_location_id,
                'origin': f"Van Return: {self.name}",
                'move_ids_without_package': move_lines,
                'company_id': company.id,
            }
            picking = self.env['stock.picking'].create(picking_vals)
            self.stock_picking_id = picking.id

    def action_view_stock_picking(self):
        self.ensure_one()
        if not self.stock_picking_id:
            raise UserError(_("No Stock Return transfer found for this retirement route."))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Stock Return'),
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'res_id': self.stock_picking_id.id,
            'target': 'current',
        }

    def action_cancel(self):
        for record in self:
            if record.state == "done":
                raise UserError(_("A completed retirement route cannot be cancelled."))
            record.write({"state": "cancelled"})
        return True

    def action_reset_to_draft(self):
        for record in self:
            if record.state != "cancelled":
                raise UserError(_("Only cancelled retirement routes can be reset."))
            record.write({
                "state": "draft",
                "approved_by": False,
                "approved_date": False,
                "completed_date": False,
            })
        return True


class VanRetirementRouteLine(models.Model):
    _name = "van.retirement.route.line"
    _description = "Van Retirement Route Product"
    _order = "id"

    retirement_id = fields.Many2one(
        "van.retirement.route",
        string="Retirement Route",
        required=True,
        ondelete="cascade",
        index=True,
    )

    product_id = fields.Many2one(
        "product.product",
        string="Product",
        required=True,
        ondelete="restrict",
        index=True,
    )

    expected_quantity = fields.Float(string="Expected Quantity", default=0.0)
    actual_quantity = fields.Float(string="Actual Quantity", default=0.0)

    quantity_variance = fields.Float(
        string="Quantity Variance",
        compute="_compute_values",
        store=True,
    )

    product_uom_id = fields.Many2one(
        "uom.uom",
        string="Unit of Measure",
        related="product_id.uom_id",
        store=True,
        readonly=True,
    )

    currency_id = fields.Many2one(
        "res.currency",
        related="retirement_id.currency_id",
        store=True,
        readonly=True,
    )

    sales_price = fields.Float(
        string="Sales Price",
        default=0.0,
    )

    expected_revenue = fields.Float(
        string="Expected Revenue",
        compute="_compute_values",
        store=True,
    )

    actual_revenue = fields.Float(
        string="Actual Revenue",
        compute="_compute_values",
        store=True,
    )

    revenue_variance = fields.Float(
        string="Revenue Variance",
        compute="_compute_values",
        store=True,
    )

    @api.depends("expected_quantity", "actual_quantity", "sales_price")
    def _compute_values(self):
        for line in self:
            line.quantity_variance = line.actual_quantity - line.expected_quantity
            line.expected_revenue = line.expected_quantity * line.sales_price
            line.actual_revenue = line.actual_quantity * line.sales_price
            line.revenue_variance = line.actual_revenue - line.expected_revenue


class VanRetirementRouteStop(models.Model):
    _name = "van.retirement.route.stop"
    _description = "Van Retirement Route Stop"
    _order = "sequence, id"

    retirement_id = fields.Many2one(
        "van.retirement.route",
        string="Retirement Route",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(string="Sequence", default=10)
    partner_id = fields.Many2one("res.partner", string="Customer")
    stop_name = fields.Char(string="Stop")
    planned_arrival = fields.Datetime(string="Planned Arrival")
    actual_arrival = fields.Datetime(string="Actual Arrival")
    status = fields.Selection([
        ("pending", "Pending"),
        ("visited", "Visited"),
        ("skipped", "Skipped"),
    ], string="Status", default="pending")
    note = fields.Text(string="Notes")