from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProjectManufacturingRequest(models.Model):
    _name = "project.manufacturing.request"
    _description = "Project Material Request"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "id desc"
    _rec_name = "name"

    name = fields.Char(
        string="Sequence",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New")
    )

    task_id = fields.Many2one(
        "project.task",
        string="Task",
        required=True,
        ondelete="cascade",
        index=True,
    )

    project_id = fields.Many2one(
        related="task_id.project_id",
        string="Project",
        store=True,
        readonly=True,
    )

    partner_id = fields.Many2one(
        "res.partner",
        string="Vendor",
        domain="[('supplier_rank', '>', 0)]",
        tracking=True,
    )

    line_ids = fields.One2many(
        "project.manufacturing.request.line",
        "request_id",
        string="Product Requests",
        copy=True,
    )

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("wait_approval", "Wait for Approval"),
            ("submitted", "Submitted"),
            ("done", "Done"),
        ],
        string="Status",
        required=True,
        default="draft",
        tracking=True,
    )

    request_date = fields.Datetime(
        string="Request Date",
        readonly=True,
    )

    submitted_by = fields.Many2one(
        "res.users",
        string="Submitted By",
        readonly=True,
    )

    notes = fields.Text(string="Notes")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "project.manufacturing.request.sequence"
                ) or _("New")
        return super().create(vals_list)

    def action_approve(self):
        for record in self:
            if record.state != "wait_approval":
                raise UserError(
                    _("Only requests waiting for approval can be approved.")
                )
            record.state = "submitted"
            record.request_date = fields.Datetime.now()
            record.submitted_by = self.env.user.id
            if record.task_id:
                record.task_id.manufacturer_request_state = "submitted"
        return True

    # 1. ISSUE OUT (Validate Stock na kutoa bidhaa)
    def action_issue_out(self):
        self.ensure_one()
        if self.state != "submitted":
            raise UserError(_("Request must be in Submitted state to Issue Out."))

        for line in self.line_ids:
            if line.product_id.type in ['product', 'consu']:
                if line.product_id.qty_available < line.quantity:
                    raise UserError(
                        _("Not enough stock for product '%s'. Available: %s, Requested: %s.\n"
                          "Please consider using 'Internal Transfer' or 'Create PO'.") %
                        (line.product_id.display_name, line.product_id.qty_available, line.quantity)
                    )

        self.state = "done"
        if self.task_id:
            self.task_id.manufacturer_request_state = "done"
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Materials have been successfully issued out! 🎉'),
                'type': 'success',
                'sticky': False,
            }
        }

    # 2. INTERNAL TRANSFER
    def action_internal_transfer(self):
        self.ensure_one()
        if self.state != "submitted":
            raise UserError(_("Request must be in Submitted state."))
        
        raise UserError(_("Internal Transfer feature is triggered. You can configure picking creation here."))

    # 3. CREATE PURCHASE ORDER
    def action_create_purchase_order(self):
        self.ensure_one()
        if self.state != "submitted":
            raise UserError(_("Request must be in Submitted state."))

        if not self.partner_id:
            raise UserError(_("Please select a Vendor (Supplier) before creating a Purchase Order."))

        if 'purchase.order' not in self.env:
            raise UserError(_("The Purchase module is not installed."))

        po_vals = {
            'partner_id': self.partner_id.id,
            'origin': self.name,
            'order_line': [
                (0, 0, {
                    'product_id': line.product_id.id,
                    'product_qty': line.quantity,
                    'product_uom': line.uom_id.id,
                    'price_unit': line.product_id.standard_price,
                    'name': line.product_id.display_name,
                    'date_planned': fields.Datetime.now(),
                }) for line in self.line_ids
            ]
        }
        purchase_order = self.env['purchase.order'].create(po_vals)

        return {
            'name': _('Purchase Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'res_id': purchase_order.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_reset_to_draft(self):
        for record in self:
            if record.state in ["wait_approval", "submitted"]:
                record.state = "draft"
                record.request_date = False
                record.submitted_by = False
                if record.task_id:
                    record.task_id.manufacturer_request_state = "draft"
        return True


class ProjectManufacturingRequestLine(models.Model):
    _name = "project.manufacturing.request.line"
    _description = "Project Material Request Line"

    request_id = fields.Many2one(
        "project.manufacturing.request",
        string="Material Request",
        required=True,
        ondelete="cascade",
    )

    product_id = fields.Many2one(
        "product.product",
        string="Product",
        required=True,
        domain="[('type', 'in', ['consu', 'product'])]",
    )

    quantity = fields.Float(
        string="Quantity",
        required=True,
        default=1.0,
    )

    uom_id = fields.Many2one(
        "uom.uom",
        string="Unit",
        required=True,
        compute="_compute_uom_id",
        store=True,
        readonly=False,
    )

    notes = fields.Text(string="Notes")

    @api.depends("product_id")
    def _compute_uom_id(self):
        for line in self:
            if line.product_id:
                line.uom_id = line.product_id.uom_id
            else:
                line.uom_id = False

    @api.onchange("product_id")
    def _onchange_product_id(self):
        for line in self:
            if line.product_id:
                line.uom_id = line.product_id.uom_id

    @api.constrains("quantity")
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise UserError(_("Quantity must be greater than zero."))