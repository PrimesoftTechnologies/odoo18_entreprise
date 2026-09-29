from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProjectManufacturingRequest(models.Model):
    _name = "project.manufacturing.request"
    _description = "Project Manufacturing Request"
    _order = "id desc"

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

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("done", "Manufactured"),
        ],
        string="Status",
        required=True,
        default="draft",
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

    def action_submit(self):
        for line in self:
            if line.state != "draft":
                continue

            if not line.product_id:
                raise UserError(_("Please select a product."))

            if line.quantity <= 0:
                raise UserError(_("Quantity must be greater than zero."))

            line.write({
                "state": "submitted",
                "request_date": fields.Datetime.now(),
                "submitted_by": self.env.user.id,
            })

        return True

    def action_reset_to_draft(self):
        for line in self:
            if line.state == "submitted":
                line.write({
                    "state": "draft",
                    "request_date": False,
                    "submitted_by": False,
                })
        return True

    def action_mark_manufactured(self):
        for line in self:
            if line.state != "submitted":
                raise UserError(
                    _("Only submitted manufacturing requests can be marked as manufactured.")
                )
            line.state = "done"
        return True

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        return records