# -*- coding: utf-8 -*-
"""Simple report: the classic one-sheet-per-location layout.

Excel and PDF render the same blocks, built from the engine's location sheets
(no calculation here).  One block per location (all locations when none is
selected) and, when there is more than one location, an "All Locations" block
first that adds them up.
"""
import io
import re

import xlsxwriter

from odoo import _, api, models
from odoo.exceptions import UserError

SIMPLE_HEADERS = ['Product', 'Costing', 'Begin Qty', 'Begin Value', 'In Qty', 'In Value', 'Out Qty',
                  'Out Value', 'Internal Qty', 'Internal Value', 'Adjust Qty', 'Adjust Value', 'End Qty',
                  'End Value']
SIMPLE_KEYS = ['begin_qty', 'begin_value', 'in_qty', 'in_value', 'out_qty', 'out_value',
               'int_qty', 'int_value', 'adj_qty', 'adj_value', 'end_qty', 'end_value']


def simple_blocks(env, dataset):
    """Ordered list of blocks (one per sheet / PDF page)."""
    loc = dataset.get('location_sheets') or {}
    blocks = []
    for comp in loc.get('compiled', []):
        sheets = [s for s in loc.get('sheets', []) if s['company_id'] == comp['company_id']]
        if len(sheets) > 1:
            blocks.append(_block(env._('All Locations'), comp, comp, all_locations=True))
        for sh in sheets:
            blocks.append(_block(sh['location_name'], sh, comp))
    return blocks


def _block(location_name, src, comp, all_locations=False):
    lines = [ln for g in src['groups'] for ln in g['lines']]
    lines.sort(key=lambda ln: (ln['name'].lower(), ln['product_id']))
    return {
        'location_name': location_name,
        'company_name': comp['company_name'],
        'currency': comp['currency'],
        'lines': lines,
        'totals': src['totals'],
        'all_locations': all_locations,
        'books_close_value': comp.get('books_close_value') if all_locations else None,
    }


class SimpleValuationXlsx:
    """Workbook in the exact layout of the original report (one sheet per location)."""

    def __init__(self, env, dataset):
        self.env = env
        self.ds = dataset
        self.meta = dataset['meta']

    def render(self):
        out = io.BytesIO()
        wb = xlsxwriter.Workbook(out, {'strings_to_numbers': False, 'strings_to_formulas': False,
                                       'strings_to_urls': False})
        wb.set_properties({'title': 'Inventory Valuation Report', 'author': self.meta['generated_by']})
        border = {'border': 1, 'font_name': 'Arial', 'font_size': 10}
        f = {
            'title': wb.add_format({'bold': True, 'font_size': 18, 'align': 'center', 'font_name': 'Arial'}),
            'text': wb.add_format(dict(border)),
            'header': wb.add_format(dict(border, bold=True, font_color='#FFFFFF', bg_color='#FFCC99',
                                         align='center')),
            'cell': wb.add_format(dict(border)),
            'zebra': wb.add_format(dict(border, bg_color='#C0C0C0')),
            'num': wb.add_format(dict(border, align='right', num_format='#,##0.00')),
            'zebra_num': wb.add_format(dict(border, align='right', num_format='#,##0.00', bg_color='#C0C0C0')),
            'total_text': wb.add_format(dict(border, bold=True, bg_color='#99CCFF')),
            'total': wb.add_format(dict(border, bold=True, bg_color='#99CCFF', align='right',
                                        num_format='#,##0.00')),
            'note': wb.add_format({'italic': True, 'font_size': 9, 'font_color': '#555555', 'font_name': 'Arial'}),
        }
        blocks = simple_blocks(self.env, self.ds)
        names = set()
        period = self.meta['date_from'] and '%s to %s' % (self.meta['date_from'], self.meta['date_to']) \
            or str(self.meta['date_to'])
        multi_company = len({b['company_name'] for b in blocks}) > 1
        if not blocks:
            ws = wb.add_worksheet('Inventory Valuation')
            self._sheet(ws, f, {'location_name': _('No stock locations'), 'lines': [], 'totals': {},
                                'company_name': ', '.join(c['name'] for c in self.ds['companies']),
                                'all_locations': False, 'books_close_value': None}, period)
        for block in blocks:
            label = block['location_name']
            if multi_company:
                label = '%s %s' % (block['company_name'][:10], label)
            ws = wb.add_worksheet(self._unique(names, label))
            self._sheet(ws, f, block, period)
        wb.close()
        return out.getvalue()

    @staticmethod
    def _unique(names, name):
        base = re.sub(r'[/\\]', '', name or '')
        base = re.sub(r'[\[\]:*?]', '', base).strip("' ")[:31] or 'Sheet'
        candidate, i = base, 2
        while candidate.lower() in names or candidate.lower() == 'history':
            suffix = ' (%d)' % i
            candidate = base[:31 - len(suffix)] + suffix
            i += 1
        names.add(candidate.lower())
        return candidate

    def _sheet(self, ws, f, block, period):
        ws.set_column(0, 0, 31.25)
        ws.set_column(1, 1, 15.6)
        ws.set_column(2, 13, 16.4)
        ws.freeze_panes(5, 0)
        ws.merge_range(0, 0, 0, 13, 'INVENTORY VALUATION REPORT', f['title'])
        ws.merge_range(1, 0, 1, 13, block['location_name'], f['text'])
        ws.merge_range(2, 0, 2, 13, 'Company: %s' % block['company_name'], f['text'])
        ws.merge_range(3, 0, 3, 13, 'Period: %s' % period, f['text'])
        for col, h in enumerate(SIMPLE_HEADERS):
            ws.write(4, col, h, f['header'])
        row = 5
        for i, ln in enumerate(block['lines']):
            zebra = bool(i % 2)
            ws.write_string(row, 0, ln['name'], f['zebra' if zebra else 'cell'])
            ws.write_string(row, 1, ln.get('cost_method_key') or '', f['zebra' if zebra else 'cell'])
            for col, key in enumerate(SIMPLE_KEYS, start=2):
                ws.write_number(row, col, ln[key], f['zebra_num' if zebra else 'num'])
            row += 1
        ws.merge_range(row, 0, row, 1, 'GRAND TOTAL', f['total_text'])
        for col, key in enumerate(SIMPLE_KEYS, start=2):
            value = block['totals'].get(key)
            if value is None:
                ws.write_blank(row, col, None, f['total'])   # quantities in different units are not added
            else:
                ws.write_number(row, col, value, f['total'])
        if block.get('books_close_value') is not None:
            ws.write(row + 2, 0, 'Inventory value per Odoo books (company): %s %s' % (
                '{:,.2f}'.format(block['books_close_value']), block['currency']['name']), f['note'])
        ws.write(row + 3 if block.get('books_close_value') is not None else row + 2, 0,
                 'Location values are allocated at company average cost. Internal = net transfers between '
                 'locations. End = Begin + In - Out + Internal + Adjust.', f['note'])


class SimpleValuationPdf(models.AbstractModel):
    _name = 'report.eg_inventory_valuation_report.simple_valuation_report'
    _description = 'Inventory Valuation Simple PDF Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        wizard = self.env['inventory.valuation.report'].browse(docids).exists()
        if len(wizard) != 1:
            raise UserError(_("The report parameters have expired. Please open the report wizard again."))
        dataset = wizard._get_report_dataset()
        meta = dataset['meta']
        period = meta['date_from'] and '%s to %s' % (meta['date_from'], meta['date_to']) or str(meta['date_to'])

        def fmt(v):
            if v is None:
                return ''
            return '{:,.2f}'.format(v)
        return {
            'doc_ids': wizard.ids,
            'doc_model': 'inventory.valuation.report',
            'docs': wizard,
            'blocks': simple_blocks(self.env, dataset),
            'headers': SIMPLE_HEADERS,
            'keys': SIMPLE_KEYS,
            'period': period,
            'meta': meta,
            'company_names': ', '.join(c['name'] for c in dataset['companies']),
            'fmt': fmt,
        }
