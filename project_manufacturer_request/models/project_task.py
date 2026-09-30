from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProjectTask(models.Model):
    _inherit = "project.task"

    manufacturing_line_ids = fields.One2many(
        "project.task.manufacturing.line",
        "task_id",
        string="Product Requests",
        copy=True,
    )

    manufacturer_request_count = fields.Integer(
        string="Material Requests",
        compute="_compute_manufacturer_request_count",
    )

    manufacturer_request_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("wait_approval", "Wait for Approval"),
            ("submitted", "Submitted"),
            ("done", "Done"),
        ],
        string="Material Request Status",
        default="draft",
        tracking=True,
    )

    @api.depends("manufacturing_line_ids")
    def _compute_manufacturer_request_count(self):
        for task in self:
            requests = self.env["project.manufacturing.request"].search_count([("task_id", "=", task.id)])
            task.manufacturer_request_count = requests

    def action_submit_manufacturing_request(self):
        self.ensure_one()

        lines = self.manufacturing_line_ids
        if not lines:
            raise UserError(
                _("Please add at least one Product Request before submitting.")
            )

        invalid_lines = lines.filtered(
            lambda line: line.product_id.type == "service"
        )
        if invalid_lines:
            products = ", ".join(invalid_lines.mapped("product_id.display_name"))
            raise UserError(
                _("The following products cannot be submitted for material "
                  "because they are Service products:\n%s") % products
            )

        # 1. Tengeneza Manufacturing Request Kuu (Header) ikiwa kwenye state ya 'wait_approval'
        request_vals = {
            "task_id": self.id,
            "state": "wait_approval",
        }
        main_request = self.env["project.manufacturing.request"].create(request_vals)

        # 2. Hamishia zile bidhaa kwenda kwenye zile lines za Manufacturing Request Kuu
        for line in lines:
            self.env["project.manufacturing.request.line"].create({
                "request_id": main_request.id,
                "product_id": line.product_id.id,
                "quantity": line.quantity,
                "uom_id": line.uom_id.id,
                "notes": line.notes,
            })

        # Weka state ya task kuwa wait_approval
        self.manufacturer_request_state = "wait_approval"
        
        # TUMEFUTA `self.manufacturing_line_ids.unlink()` ILI BIDHAA ZISIPOTEE BADA YA KUSUBMIT!

        # Rainbow Success Effect na jina la Sequence
        return {
            'effect': {
                'fadeout': 'slow',
                'message': _('Material Request %s Submitted (Wait for Approval)! 🎉') % main_request.name,
                'type': 'rainbow_man',
            }
        }

    def action_reset_task_manufacturing_request(self):
        self.ensure_one()
        requests = self.env["project.manufacturing.request"].search([
            ("task_id", "=", self.id), 
            ("state", "in", ["wait_approval", "submitted"])
        ])
        for req in requests:
            req.action_reset_to_draft()
        self.manufacturer_request_state = "draft"
        return True

    def action_info_missing_products(self):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Guideline'),
                'message': _('Please add the product under the Product Request tab first.'),
                'type': 'warning',
                'sticky': False,
            }
        }


# Model ya muda kwa ajili ya kushikilia bidhaa kwenye Task kabla ya kusubmit
class ProjectTaskManufacturingLine(models.Model):
    _name = "project.task.manufacturing.line"
    _description = "Project Task Material Line"

    task_id = fields.Many2one(
        "project.task",
        string="Task",
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