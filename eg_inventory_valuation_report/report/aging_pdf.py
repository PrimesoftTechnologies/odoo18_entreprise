# -*- coding: utf-8 -*-
"""PDF report models for the stock aging report (Simple and Detailed).

The templates only format figures from eg.stock.aging.engine; charts are
inline SVG built here from the same dataset (wkhtmltopdf renders SVG).
"""
import math
from markupsafe import Markup, escape

from odoo import _, api, models
from odoo.exceptions import UserError

from .aging_xlsx import BUCKET_COLORS, RISK_COLORS, aging_methodology
from .valuation_xlsx import brand_colors


def _fmt(value, digits=2, dash_zero=True):
    if value is None or value == '':
        return ''
    if dash_zero and round(value, digits) == 0:
        return '-'
    txt = '{:,.{d}f}'.format(abs(value), d=digits)
    return '-' + txt if value < 0 else txt


def svg_donut(values, colors, size=170, hole=0.58):
    total = sum(v for v in values if v > 0)
    r = size / 2.0
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">' % (size, size, size, size)]
    if total <= 0:
        parts.append('<circle cx="%s" cy="%s" r="%s" fill="#E6EBF0"/>' % (r, r, r - 2))
    else:
        angle = -math.pi / 2
        for v, c in zip(values, colors):
            if v <= 0:
                continue
            frac = v / total
            if frac >= 0.9999:
                parts.append('<circle cx="%s" cy="%s" r="%s" fill="%s"/>' % (r, r, r - 2, c))
                break
            a2 = angle + frac * 2 * math.pi
            x1, y1 = r + (r - 2) * math.cos(angle), r + (r - 2) * math.sin(angle)
            x2, y2 = r + (r - 2) * math.cos(a2), r + (r - 2) * math.sin(a2)
            large = 1 if frac > 0.5 else 0
            parts.append('<path d="M%.2f %.2f L%.2f %.2f A%.2f %.2f 0 %d 1 %.2f %.2f Z" fill="%s" stroke="#FFFFFF" '
                         'stroke-width="1.5"/>' % (r, r, x1, y1, r - 2, r - 2, large, x2, y2, c))
            angle = a2
    parts.append('<circle cx="%s" cy="%s" r="%s" fill="#FFFFFF"/>' % (r, r, r * hole))
    parts.append('</svg>')
    return Markup(''.join(parts))


def svg_stacked_bars(rows, colors, width=760, bar_h=16, label_w=170):
    """rows: [(label, [values])] -> horizontal stacked bars scaled to the largest total."""
    if not rows:
        return Markup('')
    max_total = max(sum(max(v, 0) for v in vals) for _l, vals in rows) or 1.0
    height = len(rows) * (bar_h + 8) + 6
    plot_w = width - label_w - 90
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" font-family="Helvetica,Arial,sans-serif" '
           'font-size="9">' % (width, height)]
    y = 4
    for label, vals in rows:
        out.append('<text x="%d" y="%d" text-anchor="end" fill="#33475B">%s</text>' % (
            label_w - 6, y + bar_h - 4, escape(label[:32])))
        x = label_w
        total = 0.0
        for v, c in zip(vals, colors):
            if v <= 0:
                continue
            w = plot_w * v / max_total
            out.append('<rect x="%.1f" y="%d" width="%.1f" height="%d" fill="%s"/>' % (x, y, w, bar_h, c))
            x += w
            total += v
        y += bar_h + 8
    out.append('</svg>')
    return Markup(''.join(out))


def heat_color(share):
    """White -> amber -> red for the share of a warehouse's value in an old bucket."""
    s = max(0.0, min(1.0, share))
    if s < 0.5:
        t = s / 0.5
        a, b = (255, 255, 255), (255, 217, 102)
    else:
        t = (s - 0.5) / 0.5
        a, b = (255, 217, 102), (229, 57, 53)
    return '#%02X%02X%02X' % tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


class _AgingPdfMixin(models.AbstractModel):
    _name = 'report.eg_inventory_valuation_report.aging_mixin'
    _description = 'Stock Aging PDF helpers'

    def _values(self, docids):
        wizard = self.env['stock.aging.report'].browse(docids).exists()
        if len(wizard) != 1:
            raise UserError(_("The report parameters have expired. Please open the report wizard again."))
        ds = wizard._get_report_dataset()
        primary, accent = brand_colors(ds['company_infos'][0] if ds['company_infos'] else {})
        meta = ds['meta']
        return {
            'doc_ids': wizard.ids, 'doc_model': 'stock.aging.report', 'docs': wizard, 'ds': ds, 'meta': meta,
            'primary': primary, 'accent': accent, 'cm': ds['company_infos'][0] if ds['company_infos'] else {},
            'bucket_colors': BUCKET_COLORS, 'risk_colors': RISK_COLORS,
            'fv': lambda v, d=2: _fmt(v, d), 'fz': lambda v, d=2: _fmt(v, d, dash_zero=False),
            'fq': lambda v: _fmt(v, meta['qty_digits']), 'fi': lambda v: _fmt(v, 0, dash_zero=False) if v is not None else '',
            'fp': lambda v: ('%.1f%%' % (v * 100)) if v is not None else '',
            'fd': lambda d: d.strftime('%d-%b-%Y') if d else '',
            'donut': svg_donut, 'stacked': svg_stacked_bars, 'heat': heat_color,
            'notes': aging_methodology(self.env, meta, ds['buckets']),
        }


class StockAgingSimplePdf(models.AbstractModel):
    _name = 'report.eg_inventory_valuation_report.aging_simple'
    _inherit = 'report.eg_inventory_valuation_report.aging_mixin'
    _description = 'Stock Aging Simple PDF'

    @api.model
    def _get_report_values(self, docids, data=None):
        return self._values(docids)


class StockAgingDetailedPdf(models.AbstractModel):
    _name = 'report.eg_inventory_valuation_report.aging_detailed'
    _inherit = 'report.eg_inventory_valuation_report.aging_mixin'
    _description = 'Stock Aging Detailed PDF'

    @api.model
    def _get_report_values(self, docids, data=None):
        return self._values(docids)
