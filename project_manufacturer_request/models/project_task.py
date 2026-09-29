from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProjectTask(models.Model):
    _inherit = "project.task"

    manufacturer_request_ids = fields.One2many(
        "project.manufacturing.request",
        "task_id",
        string="Product Requests",
        copy=True,
    )

    manufacturer_request_count = fields.Integer(
        string="Manufacturing Requests",
        compute="_compute_manufacturer_request_count",
    )

    manufacturer_request_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("done", "Manufactured"),
        ],
        string="Manufacturing Request Status",
        compute="_compute_manufacturer_request_state",
        store=True,
    )

    @api.depends("manufacturer_request_ids")
    def _compute_manufacturer_request_count(self):
        for task in self:
            task.manufacturer_request_count = len(task.manufacturer_request_ids)

    @api.depends("manufacturer_request_ids.state")
    def _compute_manufacturer_request_state(self):
        for task in self:
            states = task.manufacturer_request_ids.mapped("state")
            if not states:
                task.manufacturer_request_state = "draft"
            elif all(state == "done" for state in states):
                task.manufacturer_request_state = "done"
            elif "submitted" in states:
                task.manufacturer_request_state = "submitted"
            else:
                task.manufacturer_request_state = "draft"

    def action_submit_manufacturing_request(self):
        self.ensure_one()

        lines = self.manufacturer_request_ids.filtered(
            lambda line: line.state == "draft"
        )

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
                _("The following products cannot be submitted for manufacturing "
                  "because they are Service products:\n%s") % products
            )

        # Submit lines
        lines.action_submit()

        # Kurudisha Rainbow Success Effect (Confetti)
        return {
            'effect': {
                'fadeout': 'slow',
                'message': _('Manufacturing Request Submitted Successfully! 🎉'),
                'type': 'rainbow_man',
            }
        }

    def action_reset_task_manufacturing_request(self):
        self.ensure_one()
        lines = self.manufacturer_request_ids.filtered(
            lambda line: line.state == "submitted"
        )
        if lines:
            lines.action_reset_to_draft()
        return True

    def action_info_missing_products(self):
        """Fonksheni ya kitufe cha muongozo (info button)"""
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