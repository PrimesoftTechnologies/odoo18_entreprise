from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    oscon_po_approver_ids = fields.Many2many(
        related='company_id.oscon_po_approver_ids', readonly=False,
        string='Purchase Order Approvers')
    oscon_po_approval_mode = fields.Selection(
        related='company_id.oscon_po_approval_mode', readonly=False,
        string='Approval Rule')
