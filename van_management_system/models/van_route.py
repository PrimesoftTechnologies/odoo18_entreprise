# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class VanRoute(models.Model):
    _name = "van.route"
    _description = "Van Distribution Route"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "route_date desc, id desc"

    name = fields.Char(string="Route Reference", 
    required=True, 
    copy=False, 
    readonly=True, 
    default=lambda self: _("New"), 
    tracking=True)
    
    route_date = fields.Date(string="Route Date", required=True, default=fields.Date.context_today, tracking=True)
    company_id = fields.Many2one("res.company", string="Company", required=True, default=lambda self: self.env.company, readonly=True)

    van_id = fields.Many2one("fleet.vehicle", string="Van", required=True, tracking=True, domain=[("is_van", "=", True), ("van_active", "=", True)])
    salesman_id = fields.Many2one("res.users", string="Salesman", related="van_id.van_salesman_id", store=True, readonly=True)
    supervisor_id = fields.Many2one("res.users", string="Supervisor", related="van_id.van_supervisor_id", store=True, readonly=True)
    
    # POS Config iliyounganishwa na gari hili
    pos_config_id = fields.Many2one("pos.config", related="van_id.van_pos_config_id", string="POS Config", store=True, readonly=True)
    pos_session_id = fields.Many2one("pos.session", string="POS Session", readonly=True, copy=False)

    start_location = fields.Char(string="Start Location", required=True, tracking=True)
    end_location = fields.Char(string="End Location", tracking=True)

    internal_transfer_id = fields.Many2one("stock.picking", string="Internal Transfer", tracking=True)
    stock_transfer_id = fields.Many2one(
        "van.stock.transfer",
        string="Stock Transfer",
        tracking=True,
        index=True,
        ondelete="set null",
    )
    internal_transfer_state = fields.Selection(related="internal_transfer_id.state", string="Transfer Status", readonly=True)

    product_line_ids = fields.One2many("van.route.product", "route_id", string="Products", copy=False)
    product_count = fields.Integer(string="Products", compute="_compute_product_count")
    total_expected_revenue = fields.Float(string="Expected Revenue", compute="_compute_total_expected_revenue")

    state = fields.Selection([
        ("draft", "Draft"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ], string="Status", default="draft", required=True, tracking=True)

    note = fields.Text(string="Notes")

    @api.depends("product_line_ids")
    def _compute_product_count(self):
        for route in self:
            route.product_count = len(route.product_line_ids)

    @api.depends("product_line_ids.expected_revenue")
    def _compute_total_expected_revenue(self):
        for route in self:
            route.total_expected_revenue = sum(route.product_line_ids.mapped("expected_revenue"))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals.get("name") == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code("van.route") or _("New")
            if not vals.get("company_id"):
                vals["company_id"] = self.env.company.id
        return super().create(vals_list)

    def action_start(self):
        for route in self:
            if route.state != "draft":
                raise UserError(_("Only Draft routes can be started."))
            route.state = "in_progress"
        return True

    def action_start_pos_session(self):
        self.ensure_one()
        if not self.pos_config_id:
            raise UserError(_("No POS Configuration is linked to this Van! Please configure it in the Fleet settings."))
        
        # Tafuta session iliyo wazi au fungua mpya kwa ajili ya salesman au config hii
        session = self.env['pos.session'].search([
            ('config_id', '=', self.pos_config_id.id),
            ('state', 'in', ('opening_control', 'opened', 'new'))
        ], limit=1)

        if not session:
            session = self.env['pos.session'].create({
                'config_id': self.pos_config_id.id,
                'user_id': self.salesman_id.id if self.salesman_id else self.env.user.id,
            })
            
        self.pos_session_id = session.id

        # Peleka mtumiaji moja kwa moja kwenye skrini ya POS (POS UI) pamoja na session_id na config_id
        return {
            'type': 'ir.actions.act_url',
            'url': f'/pos/ui?config_id={self.pos_config_id.id}&session_id={session.id}',
            'target': 'self',
        }

    def action_complete(self):
        self.ensure_one()
        if self.state != "in_progress":
            raise UserError(_("Only routes In Progress can be completed."))
            
        return {
            "type": "ir.actions.act_window",
            "name": _("Complete Route Details"),
            "res_model": "van.route.complete.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_route_id": self.id},
        }

    def action_cancel(self):
        for route in self:
            if route.state == "completed":
                raise UserError(_("A completed route cannot be cancelled."))
            route.state = "cancelled"
        return True


class VanRouteProduct(models.Model):
    _name = "van.route.product"
    _description = "Van Route Product"
    _order = "id"

    route_id = fields.Many2one("van.route", string="Route", required=True, ondelete="cascade", index=True)
    move_id = fields.Many2one("stock.move", string="Stock Move", readonly=True, ondelete="set null")
    product_id = fields.Many2one("product.product", string="Product", required=True, index=True)
    quantity = fields.Float(string="Quantity", readonly=True, digits="Product Unit of Measure")
    approved_quantity = fields.Float(string="Approved Quantity", readonly=True, digits="Product Unit of Measure")
    
    sales_price = fields.Float(string="Sales Price", digits="Product Price")
    
    expected_revenue = fields.Float(string="Expected Revenue", compute="_compute_expected_revenue", store=True, readonly=True, digits="Product Price")
    product_uom_id = fields.Many2one("uom.uom", string="Unit", related="move_id.product_uom", readonly=True)

    @api.depends("approved_quantity", "sales_price")
    def _compute_expected_revenue(self):
        for line in self:
            line.expected_revenue = line.approved_quantity * line.sales_price


# ============================================================================
# COMPLETE ROUTE WIZARD (Inachota POS maalum kwa Salesman na Kujaza Actual Sales)
# ============================================================================

class VanRouteCompleteWizard(models.TransientModel):
    _name = "van.route.complete.wizard"
    _description = "Complete Route Wizard"

    route_id = fields.Many2one("van.route", string="Sales Route", required=True)
    salesman_id = fields.Many2one("res.users", related="route_id.salesman_id", readonly=True)
    end_location = fields.Char(string="End Location", required=True)
    
    # Domain inaonyesha POS Session za Salesman huyu pekee
    pos_session_id = fields.Many2one(
        "pos.session", 
        string="POS Session / ID", 
        required=True, 
        tracking=True,
        domain="[('user_id', '=', salesman_id)]"
    )
    
    route_reference = fields.Char(string="Route Reference / ID", related="route_id.name", readonly=True)

    def action_confirm_complete_route(self):
        self.ensure_one()
        
        # ==========================================================
        # UKAGUZI WA POS ID: Kuzuia isitumike mara mbili kwenye Retirement
        # ==========================================================
        if self.pos_session_id:
            pos_name = self.pos_session_id.name.strip()
            
            # Tunatafuta kama POS Session hii imeshawahi kutumika kwenye rekodi nyingine HAI 
            # (bila kuhesabu rekodi zilizofutwa au route hii ya sasa)
            existing = self.env["van.retirement.route"].search([
                ("pos_session_ref", "=", pos_name),
                ("state", "in", ("submitted", "approved", "done")),
                ("route_id", "!=", self.route_id.id)
            ], limit=1)
            
            if existing:
                raise ValidationError(_(
                    f"POS ID / Session '{pos_name}' Sorry! This POS ID is already used in another "
                    f"Retirement record (Ref: {existing.name}). Not allowed to complete!"
                ))

        # ==========================================================
        # KAMA HAIJATUMIKA KWENYE ROUTE NYINGINE, ENDELEA
        # ==========================================================
        route = self.route_id
        
        route.write({
            "end_location": self.end_location,
            "state": "completed",
        })

        pos_name = self.pos_session_id.name if self.pos_session_id else ""

        retirement = self.env["van.retirement.route"].search([("route_id", "=", route.id)], limit=1)
        if not retirement:
            retirement = self.env["van.retirement.route"].create({
                "route_id": route.id,
                "route_date": route.route_date,
                "company_id": route.company_id.id,
                "pos_session_ref": pos_name,
            })
        else:
            retirement.write({"pos_session_ref": pos_name})

        # Kusoma Mauzo Otomatiki kutoka kwenye POS Session iliyochaguliwa
        if self.pos_session_id and retirement.product_line_ids:
            sold_quantities = {}
            pos_orders = self.env["pos.order"].search([("session_id", "=", self.pos_session_id.id)])
            
            for order in pos_orders:
                for line in order.lines:
                    prod = line.product_id
                    if prod:
                        sold_quantities[prod.id] = sold_quantities.get(prod.id, 0.0) + line.qty

            for ret_line in retirement.product_line_ids:
                prod_id = ret_line.product_id.id
                if prod_id in sold_quantities:
                    ret_line.write({"actual_quantity": sold_quantities[prod_id]})

        return {
            "type": "ir.actions.act_window",
            "name": _("Van Route Retirement"),
            "res_model": "van.retirement.route",
            "view_mode": "form",
            "res_id": retirement.id,
            "target": "current",
        }