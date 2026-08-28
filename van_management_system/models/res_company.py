from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    van_transfer_approver_ids = fields.Many2many(
        "res.users",
        "res_company_van_transfer_approver_rel",
        "company_id",
        "user_id",
        string="Van Transfer Approvers",
        help="Users assigned to approve Van Stock Transfers for this company.",
    )