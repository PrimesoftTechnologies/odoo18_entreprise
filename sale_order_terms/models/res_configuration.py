from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    sale_terms_html = fields.Html(
        string="Default Sale Terms and Conditions", translate=True, store=True
    )


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    use_sale_terms = fields.Boolean(
        default=False,
        readonly=False,
        config_parameter="sale_order_terms.use_sale_terms",
    )
    sale_terms_html = fields.Html(
        related="company_id.sale_terms_html",
        string="Purchase Terms & Conditions",
        readonly=False,
    )
