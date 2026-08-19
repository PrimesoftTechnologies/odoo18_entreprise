from odoo import models, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'company_id' in fields_list or 'company_id' in res or not res.get('company_id'):
            res['company_id']  = self.env.company.id
        return res