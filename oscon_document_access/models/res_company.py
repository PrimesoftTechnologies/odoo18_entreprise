from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    oscon_boss_ids = fields.Many2many(
        "res.users",
        "oscon_company_boss_rel",
        "company_id",
        "user_id",
        string="Documents Bosses / CEOs",
        domain=[("share", "=", False)],
        help="These users automatically get access to all folders and documents.",
    )
