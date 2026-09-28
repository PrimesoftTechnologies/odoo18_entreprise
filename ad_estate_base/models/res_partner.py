from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_landlord = fields.Boolean(string='Is Landlord', default=False)
    is_tenant = fields.Boolean(string='Is Tenant', default=False)
    is_buyer = fields.Boolean(string='Is Buyer', default=False)
    is_broker = fields.Boolean(string='Is Broker / Agent', default=False)
    is_subcontractor = fields.Boolean(string='Is Subcontractor', default=False)
    is_existing_member = fields.Boolean(string='Is Existing Society Member', default=False)

    pan_no = fields.Char(string='PAN Number')
    aadhaar_no = fields.Char(string='Aadhaar Number')
    kyc_verified = fields.Boolean(string='KYC Verified', default=False)
