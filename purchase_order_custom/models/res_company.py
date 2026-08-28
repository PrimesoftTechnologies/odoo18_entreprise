from odoo import api, fields, models

class ResCompany(models.Model):
    _inherit = 'res.company'

    purchase_approval_required = fields.Boolean(
        string='Purchase Approval Required',
        default=False,
    )

    procurement_manager_id = fields.Many2one(
        'res.users',
        string='Procurement Manager',
        help="Mtu mwenye mamlaka ya kuidhinisha hatua ya kwanza (Procurement)."
    )

    finance_manager_id = fields.Many2one(
        'res.users',
        string='Finance Manager',
        help="Mtu mwenye mamlaka ya kuidhinisha hatua ya pili na ya mwisho (Finance)."
    )