# -*- coding: utf-8 -*-
from odoo import _, api, models
from odoo.exceptions import UserError

from .valuation_xlsx import brand_colors, methodology_notes


def _fmt(value, digits, dash_zero=True):
    if value is None:
        return ''
    if dash_zero and round(value, digits) == 0:
        return '-'
    txt = '{:,.{d}f}'.format(abs(value), d=digits)
    return '-' + txt if value < 0 else txt


class InventoryValuationPdf(models.AbstractModel):
    _name = 'report.eg_inventory_valuation_report.stock_inventory_pdf_report'
    _description = 'Inventory Valuation PDF Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        wizard = self.env['inventory.valuation.report'].browse(docids).exists()
        if len(wizard) != 1:
            raise UserError(_("The report parameters have expired. Please open the report wizard again."))
        dataset = wizard._get_report_dataset()
        meta = dataset['meta']
        primary, accent = brand_colors(dataset['companies'][0] if dataset['companies'] else {})
        exceptions_limit = 60
        return {
            'doc_ids': wizard.ids,
            'doc_model': 'inventory.valuation.report',
            'docs': wizard,
            'ds': dataset,
            'meta': meta,
            'primary': primary,
            'accent': accent,
            'notes': methodology_notes(self.env, meta),
            'exceptions_limit': exceptions_limit,
            'fv': lambda v, d=2: _fmt(v, d),
            'fz': lambda v, d=2: _fmt(v, d, dash_zero=False),
            'fq': lambda v: _fmt(v, meta['qty_digits']),
            'fp': lambda v: _fmt(v, meta['price_digits'], dash_zero=False),
            'company_main': dataset['companies'][0] if dataset['companies'] else {},
        }
