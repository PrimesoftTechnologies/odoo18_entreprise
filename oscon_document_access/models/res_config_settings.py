from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    oscon_boss_ids = fields.Many2many(
        related="company_id.oscon_boss_ids",
        readonly=False,
        string="Bosses / CEOs",
    )

    def set_values(self):
        company = self.company_id
        old = company.sudo().oscon_boss_ids
        super().set_values()
        new = company.sudo().oscon_boss_ids

        added = new - old
        removed = old - new

        if added:
            self.env["documents.document"]._oscon_sync_company(company, added.partner_id)
        if removed:
            # remove only the access rows that this module created automatically
            self.env["documents.access"].sudo().search(
                [
                    ("oscon_auto", "=", True),
                    ("partner_id", "in", removed.partner_id.ids),
                    ("document_id.company_id", "in", [company.id, False]),
                ]
            ).unlink()
