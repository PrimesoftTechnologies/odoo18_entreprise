from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PosConfig(models.Model):
    _inherit = "pos.config"

    is_van_pos = fields.Boolean(string="Is Van POS", tracking=True)
    van_id = fields.Many2one(
        "fleet.vehicle",
        string="Van",
        tracking=True,
        domain="[('is_van', '=', True), ('van_active', '=', True)]",
    )
    van_salesman_id = fields.Many2one(
        "res.users",
        related="van_id.van_salesman_id",
        string="Van Salesman",
        readonly=True,
    )

    @api.constrains("is_van_pos", "van_id")
    def _check_van_pos(self):
        for config in self:
            if config.is_van_pos and not config.van_id:
                raise ValidationError(_("A Van POS must have a Van configured."))

            if config.is_van_pos and config.van_id:
                existing = self.search([
                    ("is_van_pos", "=", True),
                    ("van_id", "=", config.van_id.id),
                    ("id", "!=", config.id),
                ], limit=1)
                if existing:
                    raise ValidationError(
                        _("Van %s is already assigned to another Van POS.") %
                        config.van_id.display_name
                    )

    def action_assign_to_van(self):
        for config in self:
            if not config.is_van_pos or not config.van_id:
                raise ValidationError(
                    _("Enable Is Van POS and select a Van first.")
                )
            config.van_id.van_pos_config_id = config.id
        return True