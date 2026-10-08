from odoo import api, fields, models, _
from odoo.fields import Command


class SaleOrder(models.Model):
    _inherit = 'sale.order'


    @api.depends('partner_id')
    def _compute_note(self):
        use_sale_terms = self.env['ir.config_parameter'].sudo().get_param('sale_order_terms.use_sale_terms')
        if not use_sale_terms:
            return
        for order in self:
            order = order.with_company(order.company_id)
            if self.env.company.sale_terms_html:
                order.note = order.with_context(lang=order.partner_id.lang).env.company.sale_terms_html
            else:
                order.note = ''


    def _prepare_invoice(self):
        """
        Prepare the dict of values to create the new invoice for a sales order. This method may be
        overridden to implement custom invoice generation (making sure to call super() to establish
        a clean extension chain).
        """
        self.ensure_one()

        return {
            'ref': self.client_order_ref or '',
            'move_type': 'out_invoice',
            'currency_id': self.currency_id.id,
            'campaign_id': self.campaign_id.id,
            'medium_id': self.medium_id.id,
            'source_id': self.source_id.id,
            'team_id': self.team_id.id,
            'partner_id': self.partner_invoice_id.id,
            'partner_shipping_id': self.partner_shipping_id.id,
            'fiscal_position_id': (self.fiscal_position_id or self.fiscal_position_id._get_fiscal_position(self.partner_invoice_id)).id,
            'invoice_origin': self.name,
            'invoice_payment_term_id': self.payment_term_id.id,
            'invoice_user_id': self.user_id.id,
            'payment_reference': self.reference,
            'transaction_ids': [Command.set(self.transaction_ids.ids)],
            'company_id': self.company_id.id,
            'invoice_line_ids': [],
            'user_id': self.user_id.id,
        }

