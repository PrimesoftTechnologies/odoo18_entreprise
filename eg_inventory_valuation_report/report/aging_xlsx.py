# -*- coding: utf-8 -*-
"""Excel rendering of the stock aging dataset (Simple and Detailed).

No calculation happens here: every figure comes from eg.stock.aging.engine.
Values are written unrounded (displayed with 2 decimals) so that the sheet's
own formulas (Quantity x Unit Cost, SUMs, bucket IFs) reproduce the engine's
totals exactly.
"""
import io
from datetime import date

import xlsxwriter
from xlsxwriter.utility import xl_col_to_name, xl_rowcol_to_cell

from odoo import _

from .valuation_xlsx import InventoryValuationXlsx, brand_colors

BUCKET_COLORS = ['#2E7D32', '#7CB342', '#F9A825', '#FB8C00', '#E53935', '#8E0000']
RISK_COLORS = {'High': ('#FDECEA', '#B42318'), 'Medium': ('#FFF4E0', '#8A5300'),
               'Low': ('#FFFBE6', '#7A6400'), 'Healthy': ('#E6F4EA', '#1E7B34')}
EXCEL_EPOCH = date(1899, 12, 30)


def _xl_date(d):
    return (d - EXCEL_EPOCH).days if d else None


# ======================================================================
# SIMPLE — replica of the reference workbook
# ======================================================================
class SimpleAgingXlsx:
    TITLE_FILL = '#7030A0'
    HEAD_FILL = '#4472C4'
    TOTAL_FILL = '#D9EAD3'
    DATE_FILL = '#FFF2CC'
    NUM = '#,##0.00;[Red](#,##0.00);-'

    def __init__(self, env, dataset):
        self.env = env
        self.ds = dataset
        self.meta = dataset['meta']

    def render(self):
        out = io.BytesIO()
        wb = xlsxwriter.Workbook(out, {'strings_to_numbers': False, 'strings_to_formulas': False,
                                       'strings_to_urls': False})
        wb.set_properties({'title': 'Stock Aging Report', 'author': self.meta['generated_by']})
        self.wb = wb
        base = {'font_name': 'Calibri', 'font_size': 11}
        F = lambda **kw: wb.add_format(dict(base, **kw))  # noqa: E731
        self.f = {
            'title': F(bold=True, font_size=16, font_color='#FFFFFF', bg_color=self.TITLE_FILL, align='center',
                       valign='vcenter'),
            'title_left': F(bold=True, font_size=16, font_color='#FFFFFF', bg_color=self.TITLE_FILL, valign='vcenter'),
            'bold': F(bold=True),
            'date_input': F(bg_color=self.DATE_FILL, num_format='dd-mmm-yyyy', align='left'),
            'hint': F(italic=True, font_color='#666666'),
            'head': F(bold=True, font_color='#FFFFFF', bg_color=self.HEAD_FILL, align='center', valign='vcenter',
                      text_wrap=True),
            'head_left': F(bold=True, font_color='#FFFFFF', bg_color=self.HEAD_FILL),
            'text': F(),
            'qty': F(num_format='#,##0'),
            'qty_dec': F(num_format='#,##0.00'),
            'num': F(num_format=self.NUM),
            'date': F(num_format='dd-mmm-yyyy'),
            'int': F(num_format='General'),
            'remark': F(font_color='#B42318', italic=True),
            'total_label': F(bold=True, bg_color=self.TOTAL_FILL),
            'total_num': F(bold=True, bg_color=self.TOTAL_FILL, num_format=self.NUM),
            'sum_num': F(num_format='#,##0.00'),
            'pct': F(num_format='0.0%'),
            'sum_total_label': F(bold=True),
            'sum_total': F(bold=True, num_format='#,##0.00'),
            'wrap': F(text_wrap=True, valign='top'),
            'wrap_bold': F(bold=True, valign='top'),
        }
        multi = len(self.ds['companies']) > 1
        self._names = set()
        for comp, info in zip(self.ds['companies'], self.ds['company_infos']):
            suffix = (' - ' + comp['company_name']) if multi else ''
            ws = wb.add_worksheet(self._unique('Stock Aging' + suffix))
            refs = self._aging_sheet(ws, comp, info)
            self._summary_sheet(wb.add_worksheet(self._unique('Aging Summary' + suffix)), comp, refs, ws.name)
        self._instructions(wb.add_worksheet(self._unique('Instructions')))
        wb.close()
        return out.getvalue()

    def _unique(self, name):
        """Valid (max 31 chars, no []:*?/\\) and unique sheet name, e.g. for companies whose
        names only differ after the first characters."""
        import re
        base = re.sub(r'[\[\]:*?/\\]', '', name).strip("' ")[:31] or 'Sheet'
        candidate, i = base, 2
        while candidate.lower() in self._names:
            suffix = ' (%d)' % i
            candidate = base[:31 - len(suffix)] + suffix
            i += 1
        self._names.add(candidate.lower())
        return candidate

    def _logo(self, ws, logo_b64, col):
        try:
            import base64
            from PIL import Image
            raw = base64.b64decode(logo_b64)
            w, h = Image.open(io.BytesIO(raw)).size
            scale = min(36.0 / h, 110.0 / w)
            ws.insert_image(0, col, 'logo.png', {'image_data': io.BytesIO(raw), 'x_scale': scale, 'y_scale': scale,
                                                 'x_offset': 4, 'y_offset': 3, 'object_position': 3})
        except Exception:  # noqa: BLE001 - a logo must never block the report
            pass

    def _aging_sheet(self, ws, comp, info):
        f = self.f
        cur = comp['currency']['name']
        widths = [14, 24, 20, 16, 16, 18, 20, 18, 13, 17, 17, 17, 18, 18, 46]
        for i, w in enumerate(widths):
            ws.set_column(i, i, w)
        ws.set_row(0, 30)
        ws.merge_range(0, 0, 0, 13, 'STOCK AGING REPORT — %s' % comp['company_name'].upper(), f['title'])
        if info.get('logo'):
            self._logo(ws, info['logo'], 0)
        ws.write(1, 0, 'As at Date:', f['bold'])
        ws.write_number(1, 1, _xl_date(self.meta['as_of']), f['date_input'])
        ws.write(1, 3, 'Odoo snapshot as at %s. Changing the yellow date only re-ages these rows; quantities and '
                       'values stay as at the snapshot — run the report again in Odoo for another date.'
                 % self.meta['as_of'].strftime('%d-%b-%Y'), f['hint'])
        headers = ['Item Code', 'Item Description', 'Category', 'Warehouse', 'Quantity on Hand',
                   'Unit Cost (%s)' % cur, 'Stock Value (%s)' % cur, 'Last Receipt Date', 'Age (Days)',
                   '0–30 Days', '31–60 Days', '61–90 Days', '91–180 Days', 'Over 180 Days', 'Remarks']
        ws.set_row(3, 36)
        for c, h in enumerate(headers):
            ws.write(3, c, h, f['head'])
        rows = comp['simple_rows']
        integer_qty = all(abs(r['qty'] - round(r['qty'])) < 1e-9 for r in rows)
        qfmt = f['qty'] if integer_qty else f['qty_dec']
        first = 4
        r = first
        for row in rows:
            n = r + 1
            ws.write_string(r, 0, row['code'] or '', f['text'])
            ws.write_string(r, 1, row['name'], f['text'])
            ws.write_string(r, 2, row['categ'] or '', f['text'])
            ws.write_string(r, 3, row['warehouse'] or '', f['text'])
            ws.write_number(r, 4, row['qty'], qfmt)
            ws.write_number(r, 5, row['unit_cost'], f['num'])
            ws.write_formula(r, 6, '=E%d*F%d' % (n, n), f['num'], row['value'])
            if row['last_receipt']:
                ws.write_number(r, 7, _xl_date(row['last_receipt']), f['date'])
            else:
                ws.write_blank(r, 7, None, f['date'])
            # an unknown receipt date must never fall into a bucket
            ws.write_formula(r, 8, '=IF(H%d="","",MAX(0,$B$2-H%d))' % (n, n), f['int'],
                             row['age'] if row['age'] is not None else '')
            conds = ['I{n}<=30', 'AND(I{n}>30,I{n}<=60)', 'AND(I{n}>60,I{n}<=90)', 'AND(I{n}>90,I{n}<=180)',
                     'I{n}>180']
            for b, cond in enumerate(conds):
                cached = row['value'] if row['bucket'] == b else 0
                ws.write_formula(r, 9 + b, '=IF(I{n}="",0,IF({c},G{n},0))'.format(n=n, c=cond.format(n=n)),
                                 f['num'], cached)
            if row['remarks']:
                ws.write_string(r, 14, row['remarks'], f['remark'])
            r += 1
        last = r - 1
        tot = comp['simple_totals']
        ws.write(r, 1, 'TOTAL', f['total_label'])
        rng = lambda col: '=SUM(%s%d:%s%d)' % (col, first + 1, col, max(last, first) + 1)  # noqa: E731
        if tot['qty'] is not None:
            ws.write_formula(r, 4, rng('E'), f['total_num'], tot['qty'])
        else:
            ws.write(r, 4, 'mixed units', f['total_label'])
        ws.write_formula(r, 6, rng('G'), f['total_num'], tot['value'])
        for b, col in enumerate('JKLMN'):
            ws.write_formula(r, 9 + b, rng(col), f['total_num'], tot['buckets'][b])
        ws.freeze_panes(4, 0)
        ws.autofilter(3, 0, max(last, 3), 13)
        ws.set_landscape()
        ws.set_paper(9)
        ws.fit_to_pages(1, 0)
        ws.repeat_rows(3)
        return {'total_row': r + 1, 'unknown': tot['unknown']}

    def _summary_sheet(self, ws, comp, refs, aging_name):
        f = self.f
        cur = comp['currency']['name']
        tot = comp['simple_totals']
        ws.set_column(0, 0, 22)
        ws.set_column(1, 1, 22)
        ws.set_column(2, 2, 16)
        ws.set_column(3, 3, 18)
        ws.merge_range(0, 0, 0, 2, 'STOCK AGING SUMMARY', f['title_left'])
        ws.write(2, 0, 'Aging Bucket', f['head_left'])
        ws.write(2, 1, 'Stock Value (%s)' % cur, f['head_left'])
        ws.write(2, 2, '% of Total', f['head_left'])
        tr = refs['total_row']
        q = "'%s'!" % aging_name.replace("'", "''")
        labels = ['0–30 Days', '31–60 Days', '61–90 Days', '91–180 Days', 'Over 180 Days']
        row = 3
        has_unknown = abs(tot['unknown']) > 0.005
        total_row = row + len(labels) + (1 if has_unknown else 0)
        for b, (label, col) in enumerate(zip(labels, 'JKLMN')):
            ws.write(row, 0, label, f['text'])
            ws.write_formula(row, 1, '=%s%s%d' % (q, col, tr), f['sum_num'], tot['buckets'][b])
            ws.write_formula(row, 2, '=IFERROR(B%d/B%d,0)' % (row + 1, total_row + 1), f['pct'],
                             tot['buckets'][b] / tot['value'] if tot['value'] else 0)
            row += 1
        if has_unknown:
            ws.write(row, 0, 'Unknown age (no receipt date)', f['remark'])
            ws.write_formula(row, 1, '=%sG%d-SUM(%sJ%d:N%d)' % (q, tr, q, tr, tr), f['sum_num'], tot['unknown'])
            ws.write_formula(row, 2, '=IFERROR(B%d/B%d,0)' % (row + 1, total_row + 1), f['pct'],
                             tot['unknown'] / tot['value'] if tot['value'] else 0)
            row += 1
        ws.write(row, 0, 'Total Stock Value', f['sum_total_label'])
        ws.write_formula(row, 1, '=%sG%d' % (q, tr), f['sum_total'], tot['value'])
        ws.write(row + 2, 0, 'Note:', f['bold'])
        ws.merge_range(row + 2, 1, row + 3, 5,
                       'This report ages the full on-hand quantity of each item and warehouse from its last receipt '
                       'date. For receipt-level (FIFO/batch) aging, run the Detailed Stock Aging Report in Odoo.',
                       f['wrap'])
        ws.freeze_panes(3, 0)

    def _instructions(self, ws):
        f = self.f
        ws.set_column(0, 0, 24)
        ws.set_column(1, 1, 110)
        ws.merge_range(0, 0, 0, 1, 'HOW TO USE THIS REPORT', f['title_left'])
        items = [
            ('1. Reporting date', 'Cell B2 on the Stock Aging sheet shows the Odoo snapshot date (yellow). Changing it '
             're-calculates Age and buckets for the SAME quantities and values; it does not reload stock. To see stock '
             'at another date, generate the report again in Odoo (Inventory > Reporting > Stock Aging Report).'),
            ('2. Stock details', 'Item code, description, category, warehouse, quantity and unit cost come from Odoo '
             'as at the snapshot date: one row per product and warehouse (all sub-locations included). Stock owned by '
             'third parties (consignment) is excluded.'),
            ('3. Stock value', 'Calculated as Quantity on Hand × Unit Cost. The unit cost is the company inventory '
             'valuation per unit at the snapshot date (same source as the Inventory Valuation Report).'),
            ('4. Aging days', 'Reporting Date minus Last Receipt Date. The last receipt is the latest receipt into '
             'the warehouse on or before the snapshot date (purchases, production, returns, inventory counts). Stock '
             'that only arrived by internal transfer uses the company\'s last receipt before that transfer. When the '
             'last receipt is an inventory count (e.g. opening balances), Remarks says so: the stock may be older.'),
            ('5. Aging buckets', 'Stock value is allocated to exactly one bucket: 0–30, 31–60, 61–90, 91–180, or over '
             '180 days. A row without a receipt date is NOT placed in a bucket; it is flagged in Remarks and shown '
             'as "Unknown age" on the Aging Summary.'),
            ('6. Summary', 'The Aging Summary sheet totals the value in each bucket and calculates its percentage of '
             'total stock value.'),
            ('Important limitation', 'This simple report ages the entire balance of each item from one last-receipt '
             'date. If an item was received several times at different dates, older units look younger than they '
             'are. The Detailed Stock Aging Report ages each remaining receipt layer separately (FIFO / lot level) '
             'and adds demand, dead-stock and risk analysis.'),
            ('Totals', 'The total stock value equals the Inventory Valuation Report at the same date for the same '
             'products and locations (warehouse values use the company unit cost).'),
        ]
        for i, (a, b) in enumerate(items):
            ws.set_row(2 + i, 52 if i >= 6 else 34)
            ws.write(2 + i, 0, a, f['wrap_bold'])
            ws.write(2 + i, 1, b, f['wrap'])
        ws.write(2 + len(items) + 1, 0, 'Generated', f['bold'])
        ws.write(2 + len(items) + 1, 1, '%s by %s' % (self.meta['generated_at'], self.meta['generated_by']), f['text'])


# ======================================================================
# DETAILED — management workbook
# ======================================================================
class DetailedAgingXlsx(InventoryValuationXlsx):
    """Reuses the valuation workbook's design system (formats, header, logo)."""

    SHEETS = [('exec', 'Executive Summary'), ('overview', 'Aging Overview'), ('wh', 'Warehouse Analysis'),
              ('cat', 'Category Analysis'), ('slow', 'Slow-Moving'), ('dead', 'Potential Dead Stock'),
              ('capital', 'Capital Exposure'), ('replen', 'Replenishment Risk'), ('layers', 'Receipt-Level Details'),
              ('expiry', 'Expiry Analysis'), ('recon', 'Reconciliation & Exceptions'),
              ('method', 'Methodology')]

    def __init__(self, env, dataset):
        self.env = env
        self.aging = dataset
        m = dataset['meta']
        meta = dict(m, title=_('Stock Aging & Inventory Intelligence Report'),
                    period_label=_('As at %s', m['as_of_str']), price_digits=2)
        self.ds = {'companies': dataset['company_infos'], 'meta': meta}
        self.meta = meta

    def render(self):
        out = io.BytesIO()
        wb = xlsxwriter.Workbook(out, {'strings_to_numbers': False, 'strings_to_formulas': False,
                                       'strings_to_urls': False})
        wb.set_properties({'title': self.meta['title'], 'author': self.meta['generated_by']})
        self.wb = wb
        self.primary, self.accent = brand_colors(self.ds['companies'][0] if self.ds['companies'] else {})
        self._formats()
        self._extra_formats()
        has_expiry = any(c.get('expiry') and c['expiry']['rows'] for c in self.aging['companies'])
        self.sheets = {}
        for key, name in self.SHEETS:
            if key == 'expiry' and not has_expiry:
                continue
            self.sheets[key] = wb.add_worksheet(name)
        for key, ws in self.sheets.items():
            getattr(self, '_sheet_' + key)(ws)
        self.sheets['exec'].activate()
        wb.close()
        return out.getvalue()

    # ------------------------------------------------------------------
    def _extra_formats(self):
        wb = self.wb
        base = {'font_name': 'Calibri', 'font_size': 10, 'valign': 'vcenter'}
        F = lambda **kw: wb.add_format(dict(base, **kw))  # noqa: E731
        border = {'border': 1, 'border_color': '#D5DCE4'}
        self.x = {
            'kpi_label': F(bold=True, font_size=9, font_color='#5A6B7D', bg_color='#F4F7FA', text_wrap=True, **border),
            'kpi_def': F(font_size=8, font_color='#6B7C8D', text_wrap=True, valign='top', **border),
            'kpi_text': F(bold=True, font_size=12, font_color=self.primary, bg_color='#F4F7FA', **border),
            'link': F(font_color='#1F5FAD', underline=1),
            'date': F(num_format='dd-mmm-yyyy', **border),
            'date_z': F(num_format='dd-mmm-yyyy', bg_color='#F7F9FC', **border),
            'int': F(num_format='#,##0', **border),
            'pct': F(num_format='0.0%', **border),
            'pct_total': F(num_format='0.0%', bold=True, bg_color=self.primary, font_color='#FFFFFF'),
            'insight_danger': F(text_wrap=True, valign='top', font_color='#B42318', **border),
            'insight_warning': F(text_wrap=True, valign='top', font_color='#8A5300', **border),
            'insight_info': F(text_wrap=True, valign='top', font_color='#1F2D3D', **border),
            'insight_success': F(text_wrap=True, valign='top', font_color='#1E7B34', **border),
            'tag': F(bold=True, align='center', **border),
            'wrap': F(text_wrap=True, valign='top', **border),
        }
        self.risk_fmt = {k: F(bold=True, align='center', bg_color=bg, font_color=fg, **border)
                         for k, (bg, fg) in RISK_COLORS.items()}
        self.bucket_head = [F(bold=True, font_color='#FFFFFF', bg_color=c, align='center', text_wrap=True,
                              border=1, border_color='#FFFFFF') for c in BUCKET_COLORS]

    # helpers ----------------------------------------------------------
    def _companies(self):
        return self.aging['companies']

    def _cur_digits(self, comp):
        return comp['currency']['digits']

    def _sheet_header(self, ws, last_col, suffix):
        return self._header(ws, last_col, ' — ' + suffix)

    def _band(self, ws, row, last_col, text):
        ws.merge_range(row, 0, row, last_col, text, self.f['band'])
        return row + 1

    def _table(self, ws, row, cols, rows, comp, widths=True, autofilter=True, total=None, freeze=False):
        """cols: [(header, key or callable, kind, width)] kinds: text,qty,value,int,pct,date,risk,days."""
        d = self._cur_digits(comp)
        qd = self.meta['qty_digits']
        if widths:
            for i, c in enumerate(cols):
                ws.set_column(i, i, c[3])
        ws.set_row(row, 30)
        for i, c in enumerate(cols):
            ws.write(row, i, c[0], self.f['hdr'])
        hdr = row
        if freeze:
            ws.freeze_panes(row + 1, 2)
        row += 1
        first = row
        for n, r in enumerate(rows):
            z = bool(n % 2)
            for i, (head, key, kind, _w) in enumerate(cols):
                v = key(r) if callable(key) else r.get(key)
                self._cell(ws, row, i, v, kind, z, d, qd)
            row += 1
        if autofilter and rows:
            ws.autofilter(hdr, 0, row - 1, len(cols) - 1)
        if total and rows:
            for i in range(len(cols)):
                ws.write_blank(row, i, None, self.tf('total'))
            ws.write(row, 0, total, self.tf('total'))
            for i, (head, key, kind, _w) in enumerate(cols):
                if kind == 'value':
                    col = xl_col_to_name(i)
                    vals = [(key(r) if callable(key) else r.get(key)) or 0.0 for r in rows]
                    ws.write_formula(row, i, '=SUM(%s%d:%s%d)' % (col, first + 1, col, row), self.nf('value', d, 'total'),
                                     sum(vals))
            row += 1
        return row, first, hdr

    def _cell(self, ws, row, col, v, kind, z, d, qd):
        if v is None or v == '':
            ws.write_blank(row, col, None, self.tf('row', z))
        elif isinstance(v, str) and kind not in ('text', 'risk'):
            # e.g. "No demand" in a numeric column: right-aligned text, never a fake number
            ws.write_string(row, col, v, self.tf('row', z))
        elif kind == 'value':
            ws.write_number(row, col, v, self.nf('value', d, 'row', z))
        elif kind == 'qty':
            ws.write_number(row, col, v, self.nf('qty', qd, 'row', z))
        elif kind == 'num1':
            ws.write_number(row, col, v, self.nf('qty', 1, 'row', z))
        elif kind == 'int':
            ws.write_number(row, col, v, self.x['int'])
        elif kind == 'pct':
            ws.write_number(row, col, v, self.x['pct'])
        elif kind == 'date':
            ws.write_number(row, col, _xl_date(v), self.x['date_z' if z else 'date'])
        elif kind == 'risk':
            ws.write(row, col, v, self.risk_fmt.get(v, self.tf('row', z)))
        else:
            ws.write_string(row, col, str(v), self.tf('row', z))

    def _nav(self, ws, row):
        ws.write(row, 0, _('Go to:'), self.f['label'])
        col = 1
        for key, name in self.SHEETS:
            if key in self.sheets and key != 'exec':
                ws.write_url(row, col, "internal:'%s'!A1" % name, self.x['link'], string=name)
                col += 1
                if col > 6:
                    row += 1
                    col = 1
        return row + 2

    def _back(self, ws, row, col):
        ws.write_url(row, col, "internal:'Executive Summary'!A1", self.x['link'], string=_('« Executive Summary'))

    # ------------------------------------------------------------------
    # 1. Executive summary
    # ------------------------------------------------------------------
    def _sheet_exec(self, ws):
        last = 7
        for i, w in enumerate([30, 20, 48, 3, 30, 20, 48, 3]):
            ws.set_column(i, i, w)
        row = self._header(ws, last)
        row = self._nav(ws, row)
        row = self._band(ws, row, last, _('REPORT PARAMETERS'))
        for label, value in self.meta['filters']:
            ws.write(row, 0, label, self.f['label'])
            ws.merge_range(row, 1, row, last, value, self.f['value'])
            row += 1
        row += 1
        th = self.meta['thresholds']
        for comp in self._companies():
            d = self._cur_digits(comp)
            cur = comp['currency']['name']
            k = comp['kpis']
            row = self._band(ws, row, last, _('EXECUTIVE SUMMARY — %s (%s)', comp['company_name'], cur))
            tiles = [
                (_('Total inventory value'), k['total_value'], 'value', _('Book value of the stock in scope at the report date (valuation layers).')),
                (_('Products in stock'), k['products'], 'int', _('Distinct products with a positive quantity in scope.')),
                (_('Fresh inventory (0–%s days)', th[0]), k['fresh'], 'value', _('Value of stock received in the last %s days.', th[0])),
                (_('Aging inventory (%s–%s days)', th[0] + 1, th[2]), k['aging'], 'value', _('Value of stock between %s and %s days old.', th[0] + 1, th[2])),
                (_('Older than %s days', th[2]), k['over_90'], 'value', _('Capital tied up in stock older than %s days.', th[2])),
                (_('Older than %s days', th[3]), k['over_180'], 'value', _('Capital tied up in stock older than %s days.', th[3])),
                (_('Older than %s days', th[4]), k['over_365'], 'value', _('Capital tied up in stock older than %s days.', th[4])),
                (_('Capital in aged stock'), k['aged_pct'], 'pct', _('Share of dated stock value older than %s days.', th[2])),
                (_('Slow- & non-moving value'), k['slow'], 'value', _('Positions without customer/production demand for over %s days (and held at least that long), or above %s months of cover.', self.meta['slow_days'], self.meta['overstock_months'])),
                (_('Potential dead stock'), k['dead'], 'value', _('No demand for over %s days AND stock older than %s days. A management indicator, not a write-off.', self.meta['nonmoving_days'], th[3])),
                (_('Value-weighted average age'), k['wavg_age'], 'num1', _('Average age in days, weighted by value (dated stock only).')),
                (_('Oldest stock'), k['oldest_age'], 'int', _('Age in days of the oldest remaining layer: %s (%s).', k['oldest_product'] or '-', k['oldest_date'] or '-')),
                (_('Products requiring attention'), k['attention'], 'int', _('Products with a High or Medium risk score in at least one warehouse.')),
                (_('Warehouses holding aged stock'), k['aged_warehouses'], 'int', _('Warehouses with stock older than %s days.', th[3])),
                (_('Unknown / estimated age'), k['unreliable'], 'value', _('Stock dated by an inventory count (opening balances) or of unknown age; verify before acting.')),
            ]
            for i, (label, value, kind, definition) in enumerate(tiles):
                c = 0 if i % 2 == 0 else 4
                ws.set_row(row, 32)
                ws.write(row, c, label, self.x['kpi_label'])
                if kind == 'value':
                    ws.write_number(row, c + 1, value or 0.0, self.nf('value', d, 'kpi'))
                elif kind == 'pct':
                    ws.write_number(row, c + 1, value or 0.0, self.wb.add_format(
                        {'num_format': '0.0%', 'bold': True, 'font_size': 12, 'font_color': self.primary,
                         'bg_color': '#EEF3F8', 'border': 1, 'border_color': '#D5DCE4'}))
                elif kind == 'num1':
                    ws.write_number(row, c + 1, value or 0.0, self.nf('qty', 0, 'kpi'))
                else:
                    ws.write_number(row, c + 1, value or 0, self.nf('qty', 0, 'kpi'))
                ws.write(row, c + 2, definition, self.x['kpi_def'])
                if i % 2 == 1:
                    row += 1
            row += 2
            # insights
            row = self._band(ws, row, last, _('MANAGEMENT INSIGHTS'))
            for ins in comp['insights']:
                ws.set_row(row, 30)
                ws.merge_range(row, 0, row, last, '• ' + ins['text'], self.x['insight_' + ins['level']])
                row += 1
            row += 1
            # bucket table + charts
            row = self._band(ws, row, last, _('AGING DISTRIBUTION (receipt-layer)'))
            ws.write(row, 0, _('Aging bucket'), self.f['hdr'])
            ws.write(row, 1, _('Value (%s)', cur), self.f['hdr'])
            ws.write(row, 2, _('Share of dated value'), self.f['hdr'])
            row += 1
            b_first = row
            known = sum(comp['buckets_value'])
            for i, label in enumerate(self.aging['buckets']):
                ws.write(row, 0, label, self.bucket_head[i])
                ws.write_number(row, 1, comp['buckets_value'][i], self.nf('value', d))
                ws.write_formula(row, 2, '=IF(SUM($B$%d:$B$%d)=0,0,B%d/SUM($B$%d:$B$%d))' % (
                    b_first + 1, b_first + 6, row + 1, b_first + 1, b_first + 6), self.x['pct'],
                    comp['buckets_value'][i] / known if known else 0)
                row += 1
            ws.conditional_format(b_first, 2, row - 1, 2, {'type': 'data_bar', 'bar_color': '#5B9BD5',
                                                         'bar_solid': True, 'min_type': 'num', 'min_value': 0,
                                                         'max_type': 'num', 'max_value': 1})
            chart = self.wb.add_chart({'type': 'doughnut'})
            chart.add_series({'name': _('Value by age'),
                              'categories': [ws.name, b_first, 0, b_first + 5, 0],
                              'values': [ws.name, b_first, 1, b_first + 5, 1],
                              'points': [{'fill': {'color': c}} for c in BUCKET_COLORS],
                              'data_labels': {'percentage': True, 'font': {'color': '#FFFFFF', 'bold': True}}})
            chart.set_title({'name': _('Inventory value by age'), 'name_font': {'size': 11}})
            chart.set_hole_size(55)
            chart.set_legend({'position': 'right'})
            ws.insert_chart(b_first - 1, 4, chart, {'x_scale': 1.35, 'y_scale': 1.0})
            row = max(row, b_first + 15) + 2

    # ------------------------------------------------------------------
    # 2. Aging overview (product x warehouse)
    # ------------------------------------------------------------------
    def _bucket_cols(self):
        return [(lbl, (lambda i: (lambda r: r['buckets'][i]))(i), 'value', 13) for i, lbl in enumerate(self.aging['buckets'])]

    def _sheet_overview(self, ws):
        cols = [(_('Item Code'), 'code', 'text', 13), (_('Product'), 'name', 'text', 34),
                (_('Category'), 'categ', 'text', 18), (_('Warehouse'), 'warehouse', 'text', 18),
                (_('Quantity'), 'qty', 'qty', 11), (_('UoM'), 'uom', 'text', 7),
                (_('Unit Cost'), 'unit_cost', 'value', 12), (_('Stock Value'), 'value', 'value', 15)] + \
            self._bucket_cols() + [
                (_('Unknown / Negative'), lambda r: r['unknown_value'] + r['negative_value'], 'value', 12),
                (_('Avg Age (days)'), 'wavg_age', 'num1', 9), (_('Oldest Receipt'), 'oldest', 'date', 12),
                (_('Movement'), 'status_label', 'text', 12), (_('Risk'), 'risk', 'risk', 9),
                (_('Flags'), lambda r: '; '.join(r['flags']), 'text', 30)]
        row = self._header(ws, len(cols) - 1, _('Aging Overview'))
        self._back(ws, row - 1, 0)
        for comp in self._companies():
            row = self._band(ws, row, len(cols) - 1, _('%s — product × warehouse aging (%s)', comp['company_name'],
                                                      comp['currency']['name']))
            end, first, hdr = self._table(ws, row, cols, comp['rows'], comp, total=_('TOTAL'),
                                          freeze=(comp is self._companies()[0]))
            if comp['rows']:
                ws.conditional_format(first, 7, end - 2, 7, {'type': 'data_bar', 'bar_color': '#9DC3E6', 'bar_solid': True})
                for i in range(6):
                    ws.conditional_format(first, 8 + i, end - 2, 8 + i, {
                        'type': 'cell', 'criteria': '>', 'value': 0,
                        'format': self.wb.add_format({'font_color': BUCKET_COLORS[i], 'bold': i >= 4})})
            row = end + 2

    # ------------------------------------------------------------------
    # 3. Warehouses (with heatmap)
    # ------------------------------------------------------------------
    def _sheet_wh(self, ws):
        buckets = self.aging['buckets']
        cols = [(_('Warehouse'), 'warehouse', 'text', 26), (_('Stock Value'), 'value', 'value', 15),
                (_('Share of Total'), 'share', 'pct', 10)] + \
            [(lbl, (lambda i: (lambda w: w['buckets'][i]))(i), 'value', 13) for i, lbl in enumerate(buckets)] + [
                (_('Aged %% (>%s d)') % self.meta['thresholds'][2], 'aged_pct', 'pct', 10),
                (_('Avg Age (days)'), 'wavg_age', 'num1', 10), (_('Slow-moving Value'), 'slow', 'value', 14),
                (_('Dead Stock Exposure'), 'dead', 'value', 14), (_('Products'), 'products', 'int', 9)]
        row = self._header(ws, len(cols) - 1, _('Warehouse Analysis'))
        self._back(ws, row - 1, 0)
        for comp in self._companies():
            whs = comp['warehouses']
            row = self._band(ws, row, len(cols) - 1, _('%s — warehouses (%s)', comp['company_name'], comp['currency']['name']))
            end, first, hdr = self._table(ws, row, cols, whs, comp, total=_('TOTAL'))
            row = end + 1
            if not whs:
                continue
            # heatmap: share of each warehouse's dated value per bucket
            row = self._band(ws, row, len(cols) - 1, _('AGING HEATMAP — share of each warehouse\'s value by age'))
            ws.write(row, 0, _('Warehouse'), self.f['hdr'])
            for i, lbl in enumerate(buckets):
                ws.write(row, 1 + i, lbl, self.bucket_head[i])
            row += 1
            h_first = row
            for w in whs:
                ws.write(row, 0, w['warehouse'], self.tf('row'))
                for i in range(len(buckets)):
                    ws.write_number(row, 1 + i, w['shares'][i], self.x['pct'])
                row += 1
            ws.conditional_format(h_first, 4, row - 1, 6, {'type': '3_color_scale', 'min_color': '#FFFFFF',
                                                         'mid_color': '#FFD966', 'max_color': '#E53935',
                                                         'min_type': 'num', 'min_value': 0, 'mid_type': 'num',
                                                         'mid_value': 0.25, 'max_type': 'num', 'max_value': 0.75})
            ws.conditional_format(h_first, 1, row - 1, 3, {'type': '2_color_scale', 'min_color': '#FFFFFF',
                                                         'max_color': '#63BE7B', 'min_type': 'num', 'min_value': 0,
                                                         'max_type': 'num', 'max_value': 1})
            chart = self.wb.add_chart({'type': 'bar', 'subtype': 'stacked'})
            for i, lbl in enumerate(buckets):
                chart.add_series({'name': lbl, 'categories': [ws.name, first, 0, first + len(whs) - 1, 0],
                                  'values': [ws.name, first, 3 + i, first + len(whs) - 1, 3 + i],
                                  'fill': {'color': BUCKET_COLORS[i]}, 'gap': 60})
            chart.set_title({'name': _('Inventory value by warehouse and age'), 'name_font': {'size': 11}})
            chart.set_legend({'position': 'bottom'})
            chart.set_y_axis({'reverse': True})
            ws.insert_chart(row + 1, 0, chart, {'x_scale': 1.9, 'y_scale': max(1.0, 0.25 * len(whs))})
            row += 2 + max(16, int(4 * len(whs)))

    # ------------------------------------------------------------------
    # 4. Categories
    # ------------------------------------------------------------------
    def _sheet_cat(self, ws):
        buckets = self.aging['buckets']
        th = self.meta['thresholds']
        cols = [(_('Category'), 'categ', 'text', 30), (_('Stock Value'), 'value', 'value', 15),
                (_('Share of Total'), 'share', 'pct', 10)] + \
            [(lbl, (lambda i: (lambda c: c['buckets'][i]))(i), 'value', 13) for i, lbl in enumerate(buckets)] + [
                (_('Aged Value (>%s d)') % th[2], 'aged', 'value', 14), (_('Aged %'), 'aged_pct', 'pct', 9),
                (_('Slow-moving Value'), 'slow', 'value', 14), (_('Slow %'), 'slow_pct', 'pct', 9),
                (_('Dead Stock'), 'dead', 'value', 13), (_('Avg Age'), 'wavg_age', 'num1', 8),
                (_('Products'), 'products', 'int', 8),
                (_('Review'), lambda c: self.env._('Review') if c['review'] else '', 'text', 9)]
        row = self._header(ws, len(cols) - 1, _('Category Analysis'))
        self._back(ws, row - 1, 0)
        for comp in self._companies():
            cats = comp['categories']
            row = self._band(ws, row, len(cols) - 1, _('%s — product categories (%s)', comp['company_name'],
                                                      comp['currency']['name']))
            end, first, hdr = self._table(ws, row, cols, cats, comp, total=_('TOTAL'))
            if cats:
                ws.conditional_format(first, 10, end - 2, 10, {'type': 'data_bar', 'bar_color': '#F4B183', 'bar_solid': True})
                ws.conditional_format(first, len(cols) - 1, end - 2, len(cols) - 1, {
                    'type': 'cell', 'criteria': '==', 'value': '"%s"' % _('Review'), 'format': self.risk_fmt['Medium']})
                top = cats[:10]
                chart = self.wb.add_chart({'type': 'column'})
                chart.add_series({'name': _('Stock value'), 'categories': [ws.name, first, 0, first + len(top) - 1, 0],
                                  'values': [ws.name, first, 1, first + len(top) - 1, 1], 'fill': {'color': self.primary}})
                chart.add_series({'name': _('Aged value'), 'categories': [ws.name, first, 0, first + len(top) - 1, 0],
                                  'values': [ws.name, first, 9, first + len(top) - 1, 9], 'fill': {'color': '#E53935'}})
                chart.set_title({'name': _('Top categories: value vs aged value'), 'name_font': {'size': 11}})
                chart.set_legend({'position': 'bottom'})
                ws.insert_chart(end + 1, 0, chart, {'x_scale': 1.9, 'y_scale': 1.1})
                end += 18
            row = end + 2

    # ------------------------------------------------------------------
    # 5. Slow-moving / 6. dead stock
    # ------------------------------------------------------------------
    def _demand_cols(self):
        return [(_('Item Code'), 'code', 'text', 13), (_('Product'), 'name', 'text', 32),
                (_('Warehouse'), 'warehouse', 'text', 18), (_('Remaining Qty'), 'qty', 'qty', 11),
                (_('UoM'), 'uom', 'text', 7), (_('Remaining Value'), 'value', 'value', 15),
                (_('Last Sale / Consumption'), 'last_out', 'date', 13),
                (_('Days Since Movement'), 'days_since_out', 'int', 10),
                (_('Outbound Qty (history)'), 'out_qty', 'qty', 11), (_('Outbound Moves'), 'out_moves', 'int', 9),
                (_('Avg Monthly Use'), 'monthly', 'qty', 11),
                (_('Months of Cover'), lambda r: r['coverage'] if r['coverage'] is not None else self.env._('No demand'), 'num1', 10),
                (_('Oldest Stock Age'), 'oldest_age', 'int', 10), (_('Status'), 'status_label', 'text', 12),
                (_('Risk'), 'risk', 'risk', 9), (_('Score'), 'risk_score', 'int', 7)]

    def _sheet_slow(self, ws):
        cols = self._demand_cols()
        row = self._header(ws, len(cols) - 1, _('Slow-Moving & Non-Moving Inventory'))
        self._back(ws, row - 1, 0)
        for comp in self._companies():
            row = self._band(ws, row, len(cols) - 1, _(
                '%s — no customer sale or production consumption for > %s days (slow) / > %s days (non-moving); '
                'internal transfers are not demand', comp['company_name'], self.meta['slow_days'],
                self.meta['nonmoving_days']))
            end, first, hdr = self._table(ws, row, cols, comp['slow_rows'], comp, total=_('TOTAL'),
                                          freeze=comp is self._companies()[0])
            if not comp['slow_rows']:
                ws.write(row + 1, 0, _('No slow-moving inventory.'), self.f['note'])
                end = row + 2
            row = end + 2

    def _sheet_dead(self, ws):
        th = self.meta['thresholds']
        cols = [(_('Item Code'), 'code', 'text', 13), (_('Product'), 'name', 'text', 32),
                (_('Warehouse'), 'warehouse', 'text', 18), (_('Remaining Qty'), 'qty', 'qty', 11),
                (_('UoM'), 'uom', 'text', 7), (_('Inventory Value'), 'value', 'value', 15),
                (_('Original Receipt (oldest)'), 'oldest', 'date', 13),
                (_('Last Qualifying Outbound'), 'last_out', 'date', 13),
                (_('Days Without Movement'), lambda r: r['days_since_out'] if r['days_since_out'] is not None
                 else self.env._('Never'), 'int', 11),
                (_('Value > %s days') % th[3], lambda r: sum(r['buckets'][4:]), 'value', 14),
                (_('Aging Class'), lambda r: self.aging['buckets'][self._oldest_bucket(r)], 'text', 13),
                (_('Risk Level'), 'risk', 'risk', 10), (_('Score'), 'risk_score', 'int', 7),
                (_('Score: age / movement / cover'), lambda r: '%s / %s / %s' % r['risk_parts'], 'text', 14)]
        row = self._header(ws, len(cols) - 1, _('Potential Dead Stock'))
        self._back(ws, row - 1, 0)
        for comp in self._companies():
            row = self._band(ws, row, len(cols) - 1, _(
                '%s — no demand for > %s days AND stock older than %s days. Indicators for management review, '
                'not accounting write-offs.', comp['company_name'], self.meta['nonmoving_days'], th[3]))
            end, first, hdr = self._table(ws, row, cols, comp['dead_rows'], comp, total=_('TOTAL'),
                                          freeze=comp is self._companies()[0])
            if not comp['dead_rows']:
                ws.write(row + 1, 0, _('No potential dead stock found.'), self.f['note'])
                end = row + 2
            row = end + 2

    @staticmethod
    def _oldest_bucket(r):
        for i in range(5, -1, -1):
            if r['buckets'][i] > 0.005:
                return i
        return 0

    # ------------------------------------------------------------------
    # 7. Capital exposure
    # ------------------------------------------------------------------
    def _sheet_capital(self, ws):
        th = self.meta['thresholds']
        row = self._header(ws, 9, _('Capital Exposure'))
        self._back(ws, row - 1, 0)
        for i, w in enumerate([13, 34, 18, 14, 14, 14, 14, 30, 12, 12]):
            ws.set_column(i, i, w)
        for comp in self._companies():
            d = self._cur_digits(comp)
            k = comp['kpis']
            total = k['total_value']
            row = self._band(ws, row, 9, _('%s — capital tied up in aged inventory (%s)', comp['company_name'],
                                           comp['currency']['name']))
            for i, h in enumerate([_('Exposure'), _('Value'), _('Share of total')]):
                ws.write(row, i, h, self.f['hdr'])
            row += 1
            for label, v in ((_('Older than %s days', th[2]), k['over_90']), (_('Older than %s days', th[3]), k['over_180']),
                             (_('Older than %s days', th[4]), k['over_365']), (_('Potential dead stock'), k['dead']),
                             (_('Slow- and non-moving'), k['slow'])):
                ws.write(row, 0, label, self.tf('row', bold=True))
                ws.write_number(row, 1, v, self.nf('value', d))
                ws.write_number(row, 2, v / total if total else 0, self.x['pct'])
                row += 1
            conc = comp['concentration']
            ws.write(row, 0, _('Top 10 products'), self.tf('row', bold=True))
            ws.write_number(row, 1, conc['top10_value'], self.nf('value', d))
            ws.write_number(row, 2, conc['top10_share'], self.x['pct'])
            row += 2
            cols = [(_('Item Code'), 'code', 'text', 13), (_('Product'), 'name', 'text', 34),
                    (_('Category'), 'categ', 'text', 18), (_('Stock Value'), 'value', 'value', 14),
                    (_('Value > %s d') % th[2], 'aged', 'value', 14), (_('Value > %s d') % th[3], 'over_180', 'value', 14),
                    (_('Value > %s d') % th[4], 'over_365', 'value', 14),
                    (_('Warehouses with aged stock'), lambda p: ', '.join(p['warehouses']), 'text', 30),
                    (_('Avg Monthly Use'), 'monthly', 'qty', 12),
                    (_('Months of Cover'), lambda p: p['coverage'] if p['coverage'] is not None else self.env._('No demand'), 'num1', 12)]
            row = self._band(ws, row, 9, _('TOP PRODUCTS BY AGED VALUE (> %s days)', th[2]))
            end, first, hdr = self._table(ws, row, cols, comp['top_aged'], comp, widths=False, autofilter=False,
                                          total=_('TOTAL'))
            if comp['top_aged']:
                ws.conditional_format(first, 4, end - 2, 4, {'type': 'data_bar', 'bar_color': '#F8696B', 'bar_solid': True})
            row = end + 2
            row = self._band(ws, row, 9, _('POTENTIAL OVERSTOCK — cover above %s months of historical consumption',
                                           self.meta['overstock_months']))
            cols2 = [(_('Item Code'), 'code', 'text', 13), (_('Product'), 'name', 'text', 34),
                     (_('Warehouse'), 'warehouse', 'text', 18), (_('Quantity'), 'qty', 'qty', 14),
                     (_('Avg Monthly Use'), 'monthly', 'qty', 14), (_('Months of Cover'), 'coverage', 'num1', 14),
                     (_('Excess Qty'), 'excess_qty', 'qty', 14), (_('Excess Value'), 'excess_value', 'value', 30)]
            end, first, hdr = self._table(ws, row, cols2, comp['overstock'], comp, widths=False, autofilter=False,
                                          total=_('TOTAL'))
            if not comp['overstock']:
                ws.write(row + 1, 0, _('No overstock based on historical consumption.'), self.f['note'])
                end = row + 2
            row = end + 2

    # ------------------------------------------------------------------
    # 8. Replenishment risk
    # ------------------------------------------------------------------
    def _sheet_replen(self, ws):
        th = self.meta['thresholds']
        cols = [(_('Item Code'), 'code', 'text', 13), (_('Product'), 'name', 'text', 32),
                (_('Recent Receipt'), 'recent_date', 'date', 12), (_('Recent Qty'), 'recent_qty', 'qty', 11),
                (_('Recent Value'), 'recent_value', 'value', 14), (_('Receipts'), 'recent_refs', 'text', 24),
                (_('Aged Qty (> %s d)') % th[2], 'aged_qty', 'qty', 12), (_('Aged Value'), 'aged', 'value', 14),
                (_('Total Qty'), 'qty', 'qty', 11), (_('UoM'), 'uom', 'text', 7),
                (_('Months of Cover'), lambda p: p['coverage'] if p['coverage'] is not None else self.env._('No demand'), 'num1', 10),
                (_('Aged Stock Held At'), lambda p: ', '.join(p['warehouses']), 'text', 28)]
        row = self._header(ws, len(cols) - 1, _('Replenishment Risk'))
        self._back(ws, row - 1, 0)
        for comp in self._companies():
            row = self._band(ws, row, len(cols) - 1, _(
                '%s — received in the last %s days while stock older than %s days is still on hand',
                comp['company_name'], th[0], th[2]))
            end, first, hdr = self._table(ws, row, cols, comp['replenishment'], comp, total=_('TOTAL'))
            if not comp['replenishment']:
                ws.write(row + 1, 0, _('No replenishment of products holding aged stock.'), self.f['note'])
                end = row + 2
            row = end + 2

    # ------------------------------------------------------------------
    # 9. Receipt-level details
    # ------------------------------------------------------------------
    def _sheet_layers(self, ws):
        cols = [(_('Item Code'), lambda x: x['code'], 'text', 12), (_('Product'), lambda x: x['name'], 'text', 28),
                (_('Company'), lambda x: x['company'], 'text', 16), (_('Warehouse'), 'warehouse', 'text', 16),
                (_('Location'), 'location', 'text', 22), (_('Lot / Serial'), 'lot', 'text', 12),
                (_('Receipt Reference'), 'receipt_ref', 'text', 18), (_('Receipt Date'), 'receipt_date', 'date', 12),
                (_('Source'), 'source', 'text', 22), (_('Received Qty'), 'original_qty', 'qty', 11),
                (_('Consumed Qty'), 'consumed_qty', 'qty', 11), (_('Remaining Qty'), 'qty', 'qty', 11),
                (_('Unit Cost'), 'unit_cost', 'value', 11), (_('Remaining Value'), 'value', 'value', 14),
                (_('Age (days)'), 'age', 'int', 8), (_('Aging Bucket'), lambda x: x['bucket_label'], 'text', 13),
                (_('Method / Confidence'), 'confidence', 'text', 18), (_('Odoo Move Line ID'), 'ml_id', 'int', 10)]
        row = self._header(ws, len(cols) - 1, _('Receipt-Level Details'))
        self._back(ws, row - 1, 0)
        for comp in self._companies():
            pinfo = {r['product_id']: r for r in comp['rows']}
            data = []
            for lay in comp['layers']:
                pr = pinfo.get(lay['product_id'], {})
                data.append(dict(lay, code=pr.get('code', ''), name=pr.get('name', ''), company=comp['company_name'],
                                 bucket_label=self.aging['buckets'][lay['bucket']] if lay['bucket'] is not None
                                 else _('Unknown')))
            row = self._band(ws, row, len(cols) - 1, _(
                '%s — remaining receipt layers (%s listed of %s)', comp['company_name'], len(data), comp['layer_count']))
            end, first, hdr = self._table(ws, row, cols, data, comp, total=_('TOTAL'),
                                          freeze=comp is self._companies()[0])
            if data:
                ws.conditional_format(first, 14, end - 2, 14, {'type': '3_color_scale', 'min_color': '#63BE7B',
                                                             'mid_color': '#FFEB84', 'max_color': '#F8696B'})
            row = end + 2

    # ------------------------------------------------------------------
    # 10. Expiry
    # ------------------------------------------------------------------
    def _sheet_expiry(self, ws):
        cols = [(_('Item Code'), 'code', 'text', 12), (_('Product'), 'name', 'text', 30), (_('Lot'), 'lot', 'text', 14),
                (_('Warehouse'), 'warehouse', 'text', 16), (_('Location'), 'location', 'text', 22),
                (_('Quantity'), 'qty', 'qty', 11), (_('UoM'), 'uom', 'text', 7), (_('Value'), 'value', 'value', 14),
                (_('Expiry Date'), 'expiration_date', 'date', 12), (_('Days Left'), 'days_left', 'int', 9),
                (_('Status'), lambda x: {'expired': self.env._('Expired'), 'expiring': self.env._('Expiring soon'),
                                          'ok': _('OK')}[x['status']], 'text', 13),
                (_('Inventory Age (days)'), 'age', 'int', 10)]
        row = self._header(ws, len(cols) - 1, _('Expiry & Shelf-Life Analysis'))
        self._back(ws, row - 1, 0)
        for comp in self._companies():
            ex = comp.get('expiry')
            if not ex or not ex['rows']:
                continue
            d = self._cur_digits(comp)
            row = self._band(ws, row, len(cols) - 1, _('%s — lots with an expiry date (warning: %s days). Expiry is '
                                                      'not the same as inventory age.', comp['company_name'],
                                                      self.meta['expiry_days']))
            for label, v in ((_('Expired value'), ex['expired_value']), (_('Expiring soon value'), ex['expiring_value']),
                             (_('Value with expiry tracking'), ex['tracked_value'])):
                ws.write(row, 0, label, self.f['label'])
                ws.write_number(row, 1, v, self.nf('value', d, 'kpi'))
                row += 1
            row += 1
            end, first, hdr = self._table(ws, row, cols, ex['rows'], comp, total=_('TOTAL'))
            ws.conditional_format(first, 10, end - 2, 10, {'type': 'cell', 'criteria': '==',
                                                         'value': '"%s"' % _('Expired'), 'format': self.risk_fmt['High']})
            ws.conditional_format(first, 10, end - 2, 10, {'type': 'cell', 'criteria': '==',
                                                         'value': '"%s"' % _('Expiring soon'),
                                                         'format': self.risk_fmt['Medium']})
            row = end + 2

    # ------------------------------------------------------------------
    # 11. Reconciliation
    # ------------------------------------------------------------------
    def _sheet_recon(self, ws):
        row = self._header(ws, 6, _('Reconciliation & Exceptions'))
        self._back(ws, row - 1, 0)
        for i, w in enumerate([30, 14, 34, 18, 12, 15, 60]):
            ws.set_column(i, i, w)
        for comp in self._companies():
            d = self._cur_digits(comp)
            rec = comp['reconciliation']
            row = self._band(ws, row, 6, _('%s (%s) — from book value to aged value', comp['company_name'],
                                           comp['currency']['name']))
            for line in rec['lines']:
                style = 'total' if line['kind'] == 'total' else 'row'
                ws.merge_range(row, 0, row, 2, line['label'], self.tf(style, bold=line['kind'] != 'adj'))
                ws.write_number(row, 3, line['value'], self.nf('value', d, style))
                row += 1
            row += 1
            for i, h in enumerate([_('Control'), '', '', _('This report'), _('Reference'), _('Status')]):
                ws.write(row, i, h, self.f['hdr'])
            row += 1
            for chk in rec['checks']:
                ws.merge_range(row, 0, row, 2, chk['label'], self.f['value'])
                kind = 'qty' if chk.get('is_qty') else 'value'
                digits = self.meta['qty_digits'] if kind == 'qty' else d
                ws.write_number(row, 3, chk['a'], self.nf(kind, digits))
                ws.write_number(row, 4, chk['b'], self.nf(kind, digits))
                st = self._status(chk['ok'])
                ws.write(row, 5, st[0], st[1])
                row += 1
            row += 1
            cols = [(_('Exception'), 'type', 'text', 30), (_('Item Code'), 'code', 'text', 14),
                    (_('Product'), 'name', 'text', 34), (_('Warehouse'), 'warehouse', 'text', 18),
                    (_('Quantity'), 'qty', 'qty', 12), (_('Value'), 'value', 'value', 15),
                    (_('Detail'), 'detail', 'text', 60)]
            row = self._band(ws, row, 6, _('EXCEPTIONS (%s)', len(rec['exceptions'])))
            end, first, hdr = self._table(ws, row, cols, rec['exceptions'], comp, widths=False, autofilter=True)
            if not rec['exceptions']:
                ws.write(row + 1, 0, _('No exceptions.'), self.f['note'])
                end = row + 2
            row = end + 2

    # ------------------------------------------------------------------
    # 12. Methodology
    # ------------------------------------------------------------------
    def _sheet_method(self, ws):
        ws.set_column(0, 0, 130)
        row = self._header(ws, 0, _('Methodology & Instructions'))
        self._back(ws, row - 1, 0)
        for title, text in aging_methodology(self.env, self.meta, self.aging['buckets']):
            ws.write(row, 0, title, self.f['h2'])
            row += 1
            ws.write(row, 0, text, self.f['note'])
            ws.set_row(row, 15 * (1 + len(text) // 120))
            row += 2
        ws.hide_gridlines(2)


def aging_methodology(env, meta, buckets):
    _ = env._
    th = meta['thresholds']
    return [
        (_('Snapshot'), _('All quantities and values are taken as at the end of %s (%s). Values come from Odoo stock '
                          'valuation layers, like the Inventory Valuation Report. Generate a new report for another '
                          'date; editing dates in the workbook does not reload stock.', meta['as_of_str'], meta['tz'])),
        (_('Receipt-layer aging (Detailed)'), _(
            'Every done stock movement is replayed in date order. A receipt into the company (purchase, manufacturing '
            'output, inventory gain, customer return, inter-company) creates a layer dated at that receipt. Issues '
            '(sales, production consumption, scrap, losses, vendor returns) consume the oldest layers of that location '
            'first (FIFO), or the layers of the very lot/serial number when the stock is tracked. Internal transfers '
            'move layers with their original dates, so they never reset age. Consignment stock is excluded.')),
        (_('Aging buckets'), _('Age = report date − receipt date. Buckets: %s.', ', '.join(buckets))),
        (_('Simple vs Detailed'), _(
            'The Simple report ages each product/warehouse balance from its last receipt date; the Detailed report '
            'ages each remaining layer. Quantities and values are identical; only the split across buckets differs.')),
        (_('Values are never revalued'), _(
            'Physical age and financial cost are separate: each layer carries the company unit cost (book value ÷ '
            'valued quantity), whatever the costing method. FIFO-style age allocation does not mean AVCO or Standard '
            'products are revalued at FIFO cost. Warehouse values are therefore allocations at company unit cost.')),
        (_('Estimated and unknown ages'), _(
            'Stock added by an inventory adjustment (typically opening balances) is dated at the count: its true '
            'receipt date is unknown and it is flagged "Estimated". Stock transferred out of a negative location has no '
            'known receipt and is flagged "Unknown". Negative stock has no age and is shown separately.')),
        (_('Demand and movement'), _(
            'Qualifying outbound movements are customer deliveries (net of customer returns) and manufacturing '
            'consumption. Internal transfers, scrap, losses and vendor returns are not demand. Average monthly use = '
            'outbound quantity over the last %s days (or since the first receipt if shorter, minimum 30 days). Months '
            'of cover = quantity ÷ monthly use; no demand → "No demand" (never a division by zero).', meta['analysis_days'])),
        (_('Movement status'), _(
            'Non-moving: no demand for more than %s days and stock held at least that long. Slow-moving: no demand '
            'for more than %s days (or more than %s months of cover) and stock held at least that long. Recently '
            'arrived: no '
            'demand yet and held less than %s days. Movement is judged over the period the warehouse has held '
            'the product (first receipt or transfer into it), so stock transferred in recently is never "non-moving" '
            'there; its age still counts from the original receipt.', meta['nonmoving_days'], meta['slow_days'],
            meta['overstock_months'], meta['slow_days'])),
        (_('Category review flag'), _(
            'A category is flagged for review when its aged share (> %s days) is above the company average and it '
            'holds at least 5%% of the aged value, or when it holds at least 10%% of the potential dead stock.', th[2])),
        (_('Potential dead stock'), _(
            'Non-moving AND holding stock older than %s days. Age alone never makes stock dead. These are management '
            'indicators for review, not accounting write-offs.', th[3])),
        (_('Risk score (0–100)'), _(
            'Age (max 40): 40 × share older than %(t5)s d + 30 × share %(t4a)s–%(t5)s d + 15 × share %(t3a)s–%(t4)s d. '
            'Movement (max 40): never sold and held ≥ %(nm)s d → 40; no demand > %(nm)s d → 35; > %(sl)s d → 20; '
            'otherwise 0. Cover (max 20): no demand → 20; > %(ov2)s months → 20; > %(ov)s → 12; > %(ovh)s → 6. '
            'Levels: High ≥ 70, Medium 40–69, Low 20–39, Healthy < 20. New stock scores 0 on movement and cover.',
            t5=th[4], t4a=th[3] + 1, t4=th[3], t3a=th[2] + 1, nm=meta['nonmoving_days'], sl=meta['slow_days'],
            ov2=2 * meta['overstock_months'], ov=meta['overstock_months'], ovh=meta['overstock_months'] / 2)),
        (_('Replenishment risk'), _(
            'Products received (purchase, production or inter-company) in the last %s days while stock older than %s '
            'days is still on hand.', th[0], th[2])),
        (_('Reconciliation'), _(
            'Book value (valuation layers) − stock outside the selected warehouses/locations − valuation without '
            'matching physical quantity = value in this report. Each difference is listed in the exceptions with its '
            'cause; nothing is forced to reconcile.')),
        (_('Expiry'), _('Shown only for lots with an expiry date. Expiry (shelf life) is independent of inventory age.')),
    ]
