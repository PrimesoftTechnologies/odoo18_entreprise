from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    oscon_po_approver_ids = fields.Many2many(
        'res.users', 'oscon_po_company_approver_rel', 'company_id', 'user_id',
        string='Purchase Order Approvers',
        domain="[('share', '=', False)]")
    oscon_po_approval_mode = fields.Selection(
        [('all', 'All approvers must approve'),
         ('any', 'Any one approver is enough')],
        string='Purchase Approval Rule', default='all', required=True)
