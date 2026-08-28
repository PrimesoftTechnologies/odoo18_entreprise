# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class VanStockTransfer(models.Model):
    _name = "van.stock.transfer"
    _description = "Van Stock Transfer"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        string="Reference",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
    )

    transfer_type = fields.Selection(
        [
            ("load", "Stock Loading"),
            ("unload", "Stock Return / Unload"),
        ],
        string="Transfer Type",
        default="load",
        required=True,
        tracking=True,
    )

    van_id = fields.Many2one(
        "fleet.vehicle",
        string="Vehicle",
        required=True,
        tracking=True,
        domain="[('is_van', '=', True), ('van_active', '=', True)]",
    )

    salesman_id = fields.Many2one(
        "res.users",
        string="Salesman",
        related="van_id.van_salesman_id",
        store=True,
        readonly=True,
    )

    supervisor_id = fields.Many2one(
        "res.users",
        string="Supervisor",
        related="van_id.van_supervisor_id",
        store=True,
        readonly=True,
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        related="van_id.company_id",
        store=True,
        readonly=True,
    )

    source_location_id = fields.Many2one(
        "stock.location",
        string="Source Location",
        required=True,
        tracking=True,
    )

    destination_location_id = fields.Many2one(
        "stock.location",
        string="Destination Location",
        required=True,
        tracking=True,
    )

    picking_id = fields.Many2one(
        "stock.picking",
        string="Inventory Transfer",
        readonly=True,
        copy=False,
    )

    picking_count = fields.Integer(
        string="Inventory Transfers",
        compute="_compute_picking_count",
    )

    line_ids = fields.One2many(
        "van.stock.transfer.line",
        "transfer_id",
        string="Products",
        copy=True,
    )

    route_start_location = fields.Char(
        string="Start Location",
        readonly=True,
        tracking=True,
    )

    route_end_location = fields.Char(
        string="End Location",
        readonly=True,
        tracking=True,
    )

    route_start_date = fields.Datetime(
        string="Route Start Date",
        readonly=True,
        tracking=True,
    )

    route_completed_date = fields.Datetime(
        string="Route Completed Date",
        readonly=True,
        tracking=True,
    )

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("waiting_approval", "Wait for Approval"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("done", "Done"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="draft",
        tracking=True,
    )

    requested_by = fields.Many2one(
        "res.users",
        string="Requested By",
        default=lambda self: self.env.user,
        readonly=True,
    )

    approved_by = fields.Many2one(
        "res.users",
        string="Approved By",
        readonly=True,
    )

    approved_date = fields.Datetime(
        string="Approved Date",
        readonly=True,
    )

    completed_date = fields.Datetime(
        string="Completed Date",
        readonly=True,
    )

    rejection_reason = fields.Text(
        string="Rejection Reason",
        readonly=True,
        copy=False,
    )

    note = fields.Text(
        string="Notes",
    )
    route_ids = fields.One2many(
        "van.route",
        "stock_transfer_id",
        string="Routes",
    )

    route_count = fields.Integer(
        string="Routes",
        compute="_compute_route_count",
    )

    @api.depends("route_ids")
    def _compute_route_count(self):
        for rec in self:
            rec.route_count = len(rec.route_ids)

    @api.depends("picking_id")
    def _compute_picking_count(self):
        for rec in self:
            rec.picking_count = 1 if rec.picking_id else 0

    @api.onchange("van_id", "transfer_type")
    def _onchange_van_and_transfer_type(self):
        if self.van_id:
            van_loc = False
            if hasattr(self.van_id, 'van_location_id') and self.van_id.van_location_id:
                van_loc = self.van_id.van_location_id
            else:
                van_name = self.van_id.name or ""
                van_loc = self.env["stock.location"].search([
                    ('name', 'ilike', van_name),
                    ('usage', '=', 'internal')
                ], limit=1)

            wh_loc = self.env.ref('stock.stock_location_stock', raise_if_not_found=False)

            if self.transfer_type == 'unload':
                if van_loc:
                    self.source_location_id = van_loc.id
                if wh_loc:
                    self.destination_location_id = wh_loc.id
            else:
                if wh_loc:
                    self.source_location_id = wh_loc.id
                if van_loc:
                    self.destination_location_id = van_loc.id
        else:
            self.destination_location_id = False
            self.source_location_id = False

    def action_view_route_order(self):
        self.ensure_one()
        routes = self.route_ids
        if not routes:
            raise UserError(_("No route has been created for this transfer."))
        if len(routes) == 1:
            return {
                "type": "ir.actions.act_window",
                "name": _("Route"),
                "res_model": "van.route",
                "view_mode": "form",
                "res_id": routes.id,
                "target": "current",
            }
        return {
            "type": "ir.actions.act_window",
            "name": _("Routes"),
            "res_model": "van.route",
            "view_mode": "list,form",
            "domain": [("id", "in", routes.ids)],
            "target": "current",
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals.get("name") == _("New"):
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code(
                        "van.stock.transfer"
                    )
                    or _("New")
                )
            if not vals.get("transfer_type"):
                vals["transfer_type"] = "load"
                
            van_id = vals.get("van_id")
            if not van_id:
                raise ValidationError(_("Please select a Van before creating the transfer."))
            van = self.env["fleet.vehicle"].browse(van_id)
            if not van.exists():
                raise ValidationError(_("The selected Van does not exist."))
            if not van.is_van:
                raise ValidationError(_("The selected vehicle is not enabled as a Van Distribution Vehicle."))
            if not van.van_active:
                raise ValidationError(_("The selected van is not active."))
            
            van_loc = False
            if hasattr(van, 'van_location_id') and van.van_location_id:
                van_loc = van.van_location_id
            else:
                van_loc = self.env["stock.location"].search([
                    ('name', 'ilike', van.name or ''),
                    ('usage', '=', 'internal')
                ], limit=1)

            wh_loc = self.env.ref('stock.stock_location_stock', raise_if_not_found=False)

            if vals.get("transfer_type") == 'unload':
                if van_loc and not vals.get("source_location_id"):
                    vals["source_location_id"] = van_loc.id
                if wh_loc and not vals.get("destination_location_id"):
                    vals["destination_location_id"] = wh_loc.id
            else:
                if wh_loc and not vals.get("source_location_id"):
                    vals["source_location_id"] = wh_loc.id
                if van_loc and not vals.get("destination_location_id"):
                    vals["destination_location_id"] = van_loc.id

        return super().create(vals_list)

    def action_submit(self):
        for rec in self:
            if rec.state not in ("draft", "rejected"):
                raise UserError(_("Only draft or rejected transfers can be submitted."))
            if not rec.line_ids:
                raise ValidationError(_("Add at least one product."))
            rec.write({
                "state": "waiting_approval",
                "requested_by": self.env.user.id,
                "rejection_reason": False,
            })
        return True

    def _get_effective_quantity(self, line):
        if line.approved_quantity and line.approved_quantity > 0:
            return line.approved_quantity
        return line.quantity

    def action_approve(self):
        for rec in self:
            if rec.state != "waiting_approval":
                raise UserError(_("Only transfers waiting for approval can be approved."))
            
            if rec.requested_by == self.env.user:
                raise UserError(_("You cannot approve your own transfer request!"))

            rec._create_picking()
            rec.approved_by = self.env.user
            rec.approved_date = fields.Datetime.now()
            rec.state = "approved"
        return True

    def action_reject(self):
        self.ensure_one()
        if self.state != "waiting_approval":
            raise UserError(_("Only transfers waiting for approval can be rejected."))
        return {
            'name': _('Reason for Rejection'),
            'type': 'ir.actions.act_window',
            'res_model': 'van.stock.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_transfer_id': self.id}
        }

    def action_cancel(self):
        for rec in self:
            if rec.state == "done":
                raise UserError(_("Completed transfers cannot be cancelled."))
            if rec.picking_id and rec.picking_id.state not in ("cancel", "done"):
                rec.picking_id.action_cancel()
            rec.write({
                "state": "draft",
                "picking_id": False,
                "rejection_reason": False,
            })
        return True

    def action_start_route(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Start Route Details"),
            "res_model": "van.route.start.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_transfer_id": self.id},
        }

    def action_complete_route(self):
        self.ensure_one()
        route = self.route_ids.filtered(lambda r: r.state == 'in_progress')
        route_id = route[:1].id if route else (self.route_ids[:1].id if self.route_ids else False)
        
        if not route_id:
            raise UserError(_("No active route found for this transfer."))

        return {
            "type": "ir.actions.act_window",
            "name": _("Complete Route Details"),
            "res_model": "van.route.complete.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_route_id": route_id},
        }

    def _create_picking(self):
        self.ensure_one()
        if self.picking_id:
            return self.picking_id
        
        domain = [('company_id', '=', self.company_id.id)] if self.company_id else []
        picking_type = self.env['stock.picking.type'].search(domain + [('code', '=', 'internal')], limit=1)
        if not picking_type:
            picking_type = self.env['stock.picking.type'].search([], limit=1)
        if not picking_type:
            raise ValidationError(_("Please configure an Operation Type for stock transfers."))

        loc_src = self.source_location_id.id
        loc_dest = self.destination_location_id.id

        picking = self.env["stock.picking"].create({
            "picking_type_id": picking_type.id,
            "location_id": loc_src,
            "location_dest_id": loc_dest,
            "origin": self.name,
            "company_id": self.company_id.id,
        })
        
        for line in self.line_ids:
            effective_qty = self._get_effective_quantity(line)
            self.env["stock.move"].create({
                "name": self.name,
                "product_id": line.product_id.id,
                "product_uom_qty": effective_qty,
                "product_uom": line.product_uom_id.id,
                "picking_id": picking.id,
                "location_id": loc_src,
                "location_dest_id": loc_dest,
                "company_id": self.company_id.id,
            })
            
        picking.action_confirm()
        self.picking_id = picking.id
        return picking

    def action_open_picking(self):
        self.ensure_one()
        if not self.picking_id:
            raise UserError(_("No Inventory Transfer has been created yet."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Inventory Transfer"),
            "res_model": "stock.picking",
            "view_mode": "form",
            "res_id": self.picking_id.id,
            "target": "current",
        }


class VanStockTransferLine(models.Model):
    _name = "van.stock.transfer.line"
    _description = "Van Stock Transfer Line"

    transfer_id = fields.Many2one("van.stock.transfer", string="Transfer", required=True, ondelete="cascade")
    product_id = fields.Many2one("product.product", string="Product", required=True)
    quantity = fields.Float(string="Quantity", required=True, default=1.0, digits="Product Unit of Measure")
    approved_quantity = fields.Float(string="Approved Quantity", default=0.0, digits="Product Unit of Measure", tracking=True)
    
    on_hand = fields.Float(string="On Hand", compute="_compute_on_hand", store=False, digits="Product Unit of Measure")
    product_uom_id = fields.Many2one("uom.uom", string="Unit of Measure", related="product_id.uom_id", readonly=True)

    @api.depends("product_id")
    def _compute_on_hand(self):
        for line in self:
            line.on_hand = 0.0
            if line.product_id:
                quants = self.env["stock.quant"].search([
                    ("product_id", "=", line.product_id.id),
                    ("location_id.usage", '=', "internal"),
                ])
                line.on_hand = sum(quants.mapped("quantity"))

    @api.onchange("product_id")
    def _onchange_product_id(self):
        if self.product_id:
            quants = self.env["stock.quant"].search([
                ("product_id", "=", self.product_id.id),
                ("location_id.usage", '=', "internal"),
            ])
            self.on_hand = sum(quants.mapped("quantity"))


class VanStockRejectWizard(models.TransientModel):
    _name = "van.stock.reject.wizard"
    _description = "Van Stock Reject Wizard"

    transfer_id = fields.Many2one("van.stock.transfer", string="Transfer", required=True)
    reason = fields.Text(string="Reason for Rejection", required=True)

    def action_confirm_reject(self):
        self.ensure_one()
        transfer = self.transfer_id
        if transfer:
            transfer.write({
                "state": "rejected",
                "rejection_reason": self.reason,
            })
            transfer.message_post(
                body=f"<b>Transfer Rejected.</b><br/><b>Reason:</b> {self.reason}"
            )
        return {"type": "ir.actions.act_window_close"}


class VanRouteStartWizard(models.TransientModel):
    _name = "van.route.start.wizard"
    _description = "Start Route Wizard"

    transfer_id = fields.Many2one("van.stock.transfer", string="Transfer", required=True)
    route_start_location = fields.Char(string="Start Location", required=True)
    route_start_date = fields.Datetime(string="Route Start Date", required=True, default=fields.Datetime.now)

    def action_confirm_start_route(self):
        self.ensure_one()
        transfer = self.transfer_id
        if transfer:
            transfer.write({
                "route_start_location": self.route_start_location,
                "route_start_date": self.route_start_date,
            })

            route_name = self.env["ir.sequence"].next_by_code("van.route") or _("New")

            route_vals = {
                "name": route_name,
                "van_id": transfer.van_id.id,
                "start_location": self.route_start_location,
                "route_date": fields.Date.context_today(self),
                "internal_transfer_id": transfer.picking_id.id if transfer.picking_id else False,
                "stock_transfer_id": transfer.id,
                "company_id": transfer.company_id.id if transfer.company_id else self.env.company.id,
                "state": "in_progress",
            }
            route_rec = self.env["van.route"].create(route_vals)

            route_lines = []
            for line in transfer.line_ids:
                effective_qty = transfer._get_effective_quantity(line)
                route_lines.append((0, 0, {
                    "route_id": route_rec.id,
                    "product_id": line.product_id.id,
                    "quantity": line.quantity,
                    "approved_quantity": effective_qty,
                    "sales_price": line.product_id.lst_price or 0.0,
                }))
            if route_lines:
                route_rec.write({"product_line_ids": route_lines})

            return {
                "type": "ir.actions.act_window",
                "res_model": "van.route",
                "view_mode": "form",
                "res_id": route_rec.id,
                "target": "current",
            }
        return {"type": "ir.actions.act_window_close"}