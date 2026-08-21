from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    invoice_approval_required = fields.Boolean(string="Require Approval", default=False)
    invoice_approver_ids = fields.Many2many('res.users', string="Invoice Approvers")

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    invoice_approval_required = fields.Boolean(related='company_id.invoice_approval_required', readonly=False)
    invoice_approver_ids = fields.Many2many(related='company_id.invoice_approver_ids', readonly=False)