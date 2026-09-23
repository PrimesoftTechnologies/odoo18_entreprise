# -*- coding: utf-8 -*-
# Part of Kanak Infosystems LLP.
# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    use_purchase_order_note = fields.Boolean(
        string='Default(s) Terms & Conditions')
    purchase_order_note = fields.Text(
        string='Default Term(s) and Condition(s)', translate=True)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    use_purchase_order_note = fields.Boolean(
        related='company_id.use_purchase_order_note', readonly=False,
        string='Default(s) Terms & Conditions')
    purchase_order_note = fields.Text(
        related='company_id.purchase_order_note', readonly=False,
        string="Conditions &  Terms")


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    @api.model
    def _default_note(self):
        company = self.env.company
        if company.use_purchase_order_note:
            return company.purchase_order_note or ''
        return ''

    notes = fields.Text('Terms and Conditions', default=_default_note)

    @api.onchange('company_id')
    def _onchange_company_id_note(self):
        """ Hii inahakikisha terms zinabadilika au kuonekana kwa usahihi 
            kulingana na kampuni iliyochaguliwa kwenye RFQ/PO.
        """
        for order in self:
            if order.company_id and order.company_id.use_purchase_order_note:
                order.notes = order.company_id.purchase_order_note or ''
            else:
                order.notes = ''