from odoo import api, fields, models

class SaleTermsTemplate(models.Model):
    _name = 'sale.terms.template'
    _description = 'Sales Terms Template'

    name = fields.Char(string='Template Title', required=True)
    note = fields.Html(string='Terms & Conditions', required=True, translate=True)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    terms_template_id = fields.Many2one(
        'sale.terms.template', 
        string='Override Terms Template'
    )

    number_to_words = fields.Char(string="Amount in Words (Total) :",
          compute='_compute_number_to_words',
           help="To showing total amount in words")
           

    def _compute_number_to_words(self):
        """Compute the amount to words in Sale Order"""
        for rec in self:
            rec.number_to_words = rec.currency_id.amount_to_text(
                rec.amount_total)

    @api.onchange('terms_template_id')
    def _onchange_terms_template_id(self):
        """Replaces the default terms with the selected template's content"""
        if self.terms_template_id:
            self.note = self.terms_template_id.note