from odoo import fields, models


class DocumentsAccess(models.Model):
    _inherit = "documents.access"

    oscon_auto = fields.Boolean(
        string="Auto-granted to Boss",
        default=False,
        help="Created automatically by OSCON Document Access.",
    )
