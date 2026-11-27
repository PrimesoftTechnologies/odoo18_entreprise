# -*- coding: utf-8 -*-
"""Controlled-scenario tests for the inventory valuation report (fixtures in common.py)."""
import base64
import io

from odoo import Command, fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import Form, tagged

from ..report.valuation_xlsx import InventoryValuationXlsx
from .common import IvrTestCommon


@tagged('post_install', '-at_install', 'inventory_valuation_report')
class TestInventoryValuationReport(IvrTestCommon):
    # ------------------------------------------------------------------
    # report helpers
    # ------------------------------------------------------------------
    def _wizard(self, **kw):
        vals = {'start_date': '2026-10-01', 'end_date': '2026-10-31', 'company_ids': [Command.set(self.company.ids)],
                'scope': 'company'}
        for key in ('product_ids', 'category_ids', 'location_ids', 'warehouse_ids', 'company_ids'):
            if key in kw and not isinstance(kw[key], list):
                kw[key] = [Command.set(kw[key].ids)]
        vals.update(kw)
        return self.env['inventory.valuation.report'].create(vals)

    def _report(self, qty_ok=True, **kw):
        ds = self._wizard(**kw)._get_report_dataset()
        self._assert_integrity(ds, qty_ok=qty_ok)
        return ds

    @staticmethod
    def _rows(ds, section=None):
        rows = {}
        for i, sec in enumerate(ds['sections']):
            if section is not None and i != section:
                continue
            for grp in sec['groups']:
                for r in grp['rows']:
                    rows[(sec['key'], r['product_id'])] = r
        return rows

    def _row(self, ds, product, section=0):
        for i, sec in enumerate(ds['sections']):
            if i == section:
                for grp in sec['groups']:
                    for r in grp['rows']:
                        if r['product_id'] == product.id:
                            return r
        return None

    def _assert_row(self, row, expected):
        for key, value in expected.items():
            self.assertAlmostEqual(row[key], value, places=2, msg='%s: %s != %s' % (key, row[key], value))

    def _assert_integrity(self, ds, qty_ok=True):
        """Identities that must hold for every report."""
        for sec in ds['sections']:
            cur = self.env['res.currency'].browse(sec['currency']['id'])
            all_rows = []
            for grp in sec['groups']:
                for r in grp['rows']:
                    all_rows.append(r)
                    self.assertAlmostEqual(r['open_qty'] + r['in_qty'] - r['out_qty'] + r['adj_qty'], r['close_qty'],
                                           places=4, msg='qty identity %s' % r['name'])
                    self.assertTrue(cur.is_zero(r['open_value'] + r['in_value'] - r['out_value'] + r['adj_value']
                                                - r['close_value']), 'value identity %s' % r['name'])
                gsum = sum(r['close_value'] for r in grp['rows'])
                self.assertTrue(cur.is_zero(gsum - grp['totals']['close_value']))
            for k in ('open_value', 'in_value', 'out_value', 'adj_value', 'close_value'):
                self.assertTrue(cur.is_zero(sum(r[k] for r in all_rows) - sec['totals'][k]), k)
        for rec in ds['reconciliation']:
            for chk in rec['checks']:
                if chk['label'].startswith('Odoo native') and chk['ok'] is not None:
                    self.assertTrue(chk['ok'], 'report differs from native valuation: %s' % chk)
            if qty_ok and rec['qty_check']['ok'] is not None:
                self.assertTrue(rec['qty_check']['ok'], 'physical vs valued quantity: %s %s' % (
                    rec['qty_check'], [e for e in ds['exceptions'] if 'physical_qty' in e]))

    def _native(self, product, date_str, company=None):
        p = product.with_company(company or self.company).with_context(to_date=date_str)
        return p.quantity_svl, p.value_svl

    # ------------------------------------------------------------------
    # Costing methods & history
    # ------------------------------------------------------------------
    def test_01_avco_period_history_and_cutoff(self):
        p = self._product('AVCO', self.cat_avco)
        self._in(p, 10, 10.0, '2026-09-10 10:00:00')
        self._in(p, 10, 20.0, '2026-10-05 10:00:00')            # avg 15
        self._out(p, 5, '2026-10-10 10:00:00')                   # 75
        self._move(p, 4, self.stock, self.shelf, '2026-10-11 10:00:00')   # internal: not a valuation event
        self._move(p, 2, self.shelf, self.inventory_loss, '2026-10-12 10:00:00')  # 30
        self._out(p, 6, '2026-11-05 10:00:00')                   # after period: must be ignored
        ds = self._report(product_ids=p)
        self._assert_row(self._row(ds, p), {
            'open_qty': 10, 'open_value': 100, 'in_qty': 10, 'in_value': 200,
            'out_qty': 7, 'out_value': 105, 'adj_value': 0, 'close_qty': 13, 'close_value': 195, 'unit_cost': 15})
        self.assertEqual((13, 195), self._native(p, '2026-10-31 23:59:59'))
        brk = {b['type']: (b['qty'], b['value']) for b in ds['breakdown']}
        self.assertEqual(brk, {'purchase': (10, 200), 'delivery': (-5, -75), 'inventory_loss': (-2, -30)})
        # as-of reports at several dates
        asof = self._report(product_ids=p, report_type='as_of', end_date='2026-09-30')
        self._assert_row(self._row(asof, p), {'close_qty': 10, 'close_value': 100})
        asof = self._report(product_ids=p, report_type='as_of', end_date='2026-11-30')
        self._assert_row(self._row(asof, p), {'close_qty': 7, 'close_value': 105})

    def test_02_fifo_layers_and_customer_return(self):
        p = self._product('FIFO', self.cat_fifo)
        self._in(p, 10, 5.0, '2026-09-10 10:00:00')
        self._in(p, 5, 7.0, '2026-10-06 10:00:00')
        out = self._out(p, 12, '2026-10-15 10:00:00')            # 10*5 + 2*7 = 64
        self._move(p, 2, self.customer, self.stock, '2026-10-16 10:00:00', origin_move=out)
        self._in(p, 20, 9.0, '2026-11-05 10:00:00')               # after period
        ds = self._report(product_ids=p)
        row = self._row(ds, p)
        self._assert_row(row, {'open_qty': 10, 'open_value': 50, 'in_qty': 7, 'out_qty': 12, 'out_value': 64,
                               'close_qty': 5})
        qty, value = self._native(p, '2026-10-31 23:59:59')
        self.assertEqual(row['close_value'], value)
        self.assertEqual(row['close_qty'], qty)
        types = {b['type'] for b in ds['breakdown']}
        self.assertEqual(types, {'purchase', 'delivery', 'customer_return'})

    def test_03_standard_price_change_is_historical(self):
        p = self._product('STD', self.cat_std, cost=8.0)
        self._in(p, 20, None, '2026-09-10 10:00:00')
        self._out(p, 5, '2026-10-20 10:00:00')
        with self._at('2026-10-25 10:00:00'):
            p.standard_price = 10.0                               # revaluation +30 on 15 units
        with self._at('2026-11-10 10:00:00'):
            p.standard_price = 12.0                               # after the period: +30
        ds = self._report(product_ids=p)
        self._assert_row(self._row(ds, p), {
            'open_qty': 20, 'open_value': 160, 'out_qty': 5, 'out_value': 40,
            'adj_qty': 0, 'adj_value': 30, 'close_qty': 15, 'close_value': 150})
        # historical value before the change is NOT today's cost (12) times quantity
        asof = self._report(product_ids=p, report_type='as_of', end_date='2026-10-24')
        self._assert_row(self._row(asof, p), {'close_qty': 15, 'close_value': 120, 'unit_cost': 8})
        self.assertEqual([b['type'] for b in ds['breakdown'] if b['direction'] == 'adj'], ['revaluation'])

    def test_04_negative_stock_and_correction(self):
        p = self._product('NEG', self.cat_avco, cost=10.0)
        self._out(p, 5, '2026-10-02 10:00:00')                    # negative stock at 10
        asof = self._report(product_ids=p, report_type='as_of', end_date='2026-10-03')
        row = self._row(asof, p)
        self._assert_row(row, {'close_qty': -5, 'close_value': -50})
        self.assertIn('Negative stock', row['flags'])
        self.assertTrue(asof['exceptions'])
        self._in(p, 10, 16.0, '2026-10-04 10:00:00')               # vacuum: correction of the 5 units
        ds = self._report(product_ids=p)
        row = self._row(ds, p)
        qty, value = self._native(p, '2026-10-31 23:59:59')
        self.assertEqual((row['close_qty'], row['close_value']), (qty, value))
        self.assertEqual(row['close_qty'], 5)

    def test_05_cost_method_change(self):
        p = self._product('CHG', self.cat_fifo)
        self._in(p, 10, 5.0, '2026-09-10 10:00:00')
        self._in(p, 10, 7.0, '2026-09-11 10:00:00')
        with self._at('2026-10-15 10:00:00'):
            self.cat_fifo.property_cost_method = 'average'
        ds = self._report(product_ids=p)
        row = self._row(ds, p)
        self._assert_row(row, {'open_qty': 20, 'open_value': 120, 'in_qty': 0, 'out_qty': 0,
                               'adj_qty': 0, 'close_qty': 20, 'close_value': 120})
        self.assertTrue(all(b['type'] == 'cost_method_change' for b in ds['breakdown']))

    # ------------------------------------------------------------------
    # Transactions
    # ------------------------------------------------------------------
    def test_10_inventory_adjustment_scrap_vendor_return(self):
        p = self._product('ADJ', self.cat_avco)
        self._in(p, 10, 10.0, '2026-09-10 10:00:00')
        with self._at('2026-10-05 10:00:00'):
            quant = self.env['stock.quant'].with_context(inventory_mode=True).search([
                ('product_id', '=', p.id), ('location_id', '=', self.stock.id)])
            quant.inventory_quantity = 12
            quant.action_apply_inventory()                       # +2 @10
        with self._at('2026-10-06 10:00:00'):
            scrap = self.env['stock.scrap'].create({'product_id': p.id, 'scrap_qty': 1,
                                                    'location_id': self.stock.id, 'company_id': self.company.id})
            scrap.action_validate()                               # -1 @10
        self._move(p, 3, self.stock, self.supplier, '2026-10-07 10:00:00')  # vendor return -3 @10
        ds = self._report(product_ids=p)
        self._assert_row(self._row(ds, p), {'open_value': 100, 'in_qty': 2, 'in_value': 20, 'out_qty': 4,
                                            'out_value': 40, 'close_qty': 8, 'close_value': 80})
        brk = {b['type']: b['qty'] for b in ds['breakdown']}
        self.assertEqual(brk, {'inventory_gain': 2, 'scrap': -1, 'vendor_return': -3})

    def test_11_internal_transfers_company_vs_warehouse(self):
        p = self._product('INT', self.cat_avco)
        self._in(p, 10, 10.0, '2026-10-01 10:00:00')
        self._move(p, 4, self.stock, self.shelf, '2026-10-02 10:00:00')
        self._move(p, 3, self.stock, self.wh2.lot_stock_id, '2026-10-03 10:00:00')
        self._out(p, 1, '2026-10-04 10:00:00', src=self.wh2.lot_stock_id)
        company = self._report(product_ids=p)
        # internal transfers never inflate company receipts/deliveries
        self._assert_row(self._row(company, p), {'in_qty': 10, 'out_qty': 1, 'close_qty': 9, 'close_value': 90})
        per_wh = self._report(product_ids=p, scope='warehouse')
        by_label = {s['label']: s for s in per_wh['sections']}
        wh1 = [s for s in per_wh['sections'] if self.wh.name in s['label']][0]
        wh2 = [s for s in per_wh['sections'] if self.wh2.name in s['label']][0]
        r1 = wh1['groups'][0]['rows'][0]
        r2 = wh2['groups'][0]['rows'][0]
        self._assert_row(r1, {'in_qty': 10, 'out_qty': 3, 'close_qty': 7, 'close_value': 70})
        self._assert_row(r2, {'in_qty': 3, 'in_value': 30, 'out_qty': 1, 'close_qty': 2, 'close_value': 20})
        self.assertTrue(all(s['allocated'] for s in by_label.values()))
        chk = [c for c in per_wh['reconciliation'][0]['checks'] if c['label'].startswith('Sum of allocated')][0]
        self.assertTrue(chk['ok'])
        # consolidated totals eliminate the WH1 -> WH2 transfer (30): they equal
        # the company-level receipts (100) and deliveries (10)
        ct = per_wh['currency_totals'][0]
        self.assertEqual((ct['in_value'], ct['out_value'], ct['close_value'], ct['transfers_eliminated']),
                         (100, 10, 90, 30))
        # location scope: the shelf only
        loc = self._report(product_ids=p, scope='location', location_ids=self.shelf)
        self._assert_row(loc['sections'][0]['groups'][0]['rows'][0], {'in_qty': 4, 'close_qty': 4, 'close_value': 40})

    def test_12_landed_costs(self):
        if 'stock.landed.cost' not in self.env:
            self.skipTest('stock_landed_costs not installed')
        categ = self.stock_account_product_categ  # automated FIFO
        p = self._product('LC', categ)
        freight = self.env['product.product'].create({'name': 'Freight', 'type': 'service', 'landed_cost_ok': True})
        with self._at('2026-10-02 10:00:00'):
            picking = self.env['stock.picking'].create({
                'picking_type_id': self.wh.in_type_id.id, 'location_id': self.supplier.id,
                'location_dest_id': self.stock.id,
                'move_ids': [Command.create({'name': 'lc', 'product_id': p.id, 'product_uom_qty': 10,
                                             'product_uom': p.uom_id.id, 'price_unit': 10.0,
                                             'location_id': self.supplier.id, 'location_dest_id': self.stock.id})]})
            picking.action_confirm()
            picking.move_ids.quantity = 10
            picking.move_ids.picked = True
            picking.button_validate()
        with self._at('2026-10-03 10:00:00'):
            lc = self.env['stock.landed.cost'].create({
                'picking_ids': [Command.set(picking.ids)],
                'account_journal_id': self.company_data['default_journal_misc'].id,
                'cost_lines': [Command.create({'name': 'Freight', 'product_id': freight.id, 'price_unit': 50.0,
                                               'split_method': 'equal',
                                               'account_id': self.company_data['default_account_expense'].id})]})
            lc.compute_landed_cost()
            lc.button_validate()
        ds = self._report(product_ids=p)
        self._assert_row(self._row(ds, p), {'in_qty': 10, 'in_value': 100, 'adj_qty': 0, 'adj_value': 50,
                                            'close_value': 150, 'unit_cost': 15})
        self.assertEqual([b['type'] for b in ds['breakdown'] if b['direction'] == 'adj'], ['landed_cost'])

    def test_13_manufacturing_and_unbuild(self):
        if 'mrp.production' not in self.env:
            self.skipTest('mrp not installed')
        comp = self._product('COMP', self.cat_avco)
        fin = self._product('FIN', self.cat_avco)
        bom = self.env['mrp.bom'].create({'product_tmpl_id': fin.product_tmpl_id.id, 'product_qty': 1,
                                          'bom_line_ids': [Command.create({'product_id': comp.id, 'product_qty': 2})]})
        self._in(comp, 10, 4.0, '2026-10-01 10:00:00')
        with self._at('2026-10-02 10:00:00'):
            mo_form = Form(self.env['mrp.production'])
            mo_form.product_id = fin
            mo_form.bom_id = bom
            mo_form.product_qty = 3
            mo = mo_form.save()
            mo.action_confirm()
            mo_form = Form(mo)
            mo_form.qty_producing = 3
            mo = mo_form.save()
            mo.button_mark_done()
        with self._at('2026-10-03 10:00:00'):
            unbuild_form = Form(self.env['mrp.unbuild'])
            unbuild_form.mo_id = mo
            unbuild_form.product_qty = 1
            unbuild_form.save().action_unbuild()
        ds = self._report(product_ids=comp | fin)
        self._assert_row(self._row_by(ds, comp), {'in_qty': 12, 'out_qty': 6, 'close_qty': 6, 'close_value': 24})
        self._assert_row(self._row_by(ds, fin), {'in_qty': 3, 'in_value': 24, 'out_qty': 1, 'out_value': 8,
                                                 'close_qty': 2, 'close_value': 16})
        types = {(b['code'], b['type']) for b in ds['breakdown']}
        self.assertTrue({('COMP', 'consumption'), ('FIN', 'production'), ('FIN', 'unbuild_out'),
                         ('COMP', 'unbuild_in')} <= types, types)

    def _row_by(self, ds, product):
        for sec in ds['sections']:
            for grp in sec['groups']:
                for r in grp['rows']:
                    if r['product_id'] == product.id:
                        return r
        return None

    def test_14_uom_conversion_and_mixed_uom_subtotals(self):
        p = self._product('UOM', self.cat_avco)
        kg = self._product('KG', self.cat_avco, uom_id=self.env.ref('uom.product_uom_kgm').id,
                           uom_po_id=self.env.ref('uom.product_uom_kgm').id)
        self._in(p, 2, 120.0, '2026-10-01 10:00:00', uom=self.uom_dozen)   # 24 units
        self._in(kg, 5, 3.0, '2026-10-01 10:00:00')
        ds = self._report(product_ids=p | kg)
        self._assert_row(self._row_by(ds, p), {'in_qty': 24, 'close_qty': 24})
        self.assertEqual(self._row_by(ds, p)['uom'], self.uom_unit.name)
        sec = ds['sections'][0]
        self.assertIsNone(sec['totals']['close_qty'], 'quantities in different units must not be added')
        wh = self._report(product_ids=p, scope='warehouse')
        self._assert_row(wh['sections'][0]['groups'][0]['rows'][0], {'in_qty': 24, 'close_qty': 24})

    def test_15_consignment_not_valued(self):
        p = self._product('CONS', self.cat_avco)
        self._in(p, 5, 10.0, '2026-10-01 10:00:00')
        self._move(p, 7, self.supplier, self.stock, '2026-10-02 10:00:00', owner=self.partner_a)
        ds = self._report(product_ids=p)
        self._assert_row(self._row(ds, p), {'close_qty': 5, 'close_value': 50})
        wh = self._report(product_ids=p, scope='warehouse')
        self._assert_row(wh['sections'][0]['groups'][0]['rows'][0], {'close_qty': 5})

    def test_16_lot_valuation(self):
        p = self._product('LOT', self.cat_avco, tracking='lot', lot_valuated=True)
        lot_a, lot_b = [self.env['stock.lot'].create({'name': n, 'product_id': p.id, 'company_id': self.company.id})
                        for n in ('LA', 'LB')]
        self._move(p, 5, self.supplier, self.stock, '2026-10-01 10:00:00', price=10.0, lot=lot_a)
        self._move(p, 5, self.supplier, self.stock, '2026-10-01 11:00:00', price=20.0, lot=lot_b)
        self._out(p, 5, '2026-10-02 10:00:00', lot=lot_a)
        ds = self._report(product_ids=p)
        row = self._row(ds, p)
        qty, value = self._native(p, '2026-10-31 23:59:59')
        self.assertEqual((row['close_qty'], row['close_value']), (qty, value))
        self._assert_row(row, {'in_value': 150, 'close_qty': 5, 'close_value': 100})

    def test_17_physical_stock_without_valuation_is_reported(self):
        """Stock that exists physically but has no valuation layer (e.g. counted before
        stock_account was installed) must be surfaced, never silently valued or hidden."""
        valued = self._product('VAL', self.cat_avco)
        unvalued = self._product('NOVAL', self.cat_avco)
        self._in(valued, 5, 10.0, '2026-10-01 10:00:00')
        move = self._in(unvalued, 7, 3.0, '2026-10-01 10:00:00')
        self.env.cr.execute('DELETE FROM stock_valuation_layer WHERE stock_move_id = %s', (move.id,))
        self.env.invalidate_all()
        ds = self._report(product_ids=valued | unvalued, qty_ok=False)
        self.assertIsNone(self._row(ds, unvalued), 'no valuation layer: no value may be invented')
        qc = ds['reconciliation'][0]['qty_check']
        self.assertEqual((qc['ok'], qc['count']), (False, 1))
        exc = [e for e in ds['exceptions'] if e.get('physical_qty') is not None]
        self.assertEqual([(e['code'], e['physical_qty'], e['valued_qty']) for e in exc], [('NOVAL', 7, 0)])
        content = InventoryValuationXlsx(self.env, ds).render()
        self.assertTrue(content)

    def test_18_location_sheets_classic_layout(self):
        """No location selected = every stock location (sub-locations rolled up, counted once);
        In/Out external, Internal = net transfers, Adjust = counts/scrap; compiled = sum = books."""
        p = self._product('LOCS', self.cat_avco)
        self._in(p, 10, 10.0, '2026-09-20 10:00:00')                                   # opening WH1 10
        self._in(p, 6, 10.0, '2026-10-01 10:00:00')                                    # WH1 in 6
        self._move(p, 4, self.stock, self.shelf, '2026-10-02 10:00:00')               # inside WH1/Stock: not shown
        self._move(p, 3, self.stock, self.wh2.lot_stock_id, '2026-10-03 10:00:00')    # WH1 -> WH2
        self._out(p, 1, '2026-10-04 10:00:00', src=self.wh2.lot_stock_id)            # WH2 delivery
        self._move(p, 2, self.shelf, self.inventory_loss, '2026-10-05 10:00:00')      # WH1 count loss
        ds = self._report(product_ids=p, location_sheets=True)
        loc = ds['location_sheets']
        by_name = {sh['location_name']: sh['groups'][0]['lines'][0] for sh in loc['sheets']}
        self.assertEqual(set(by_name), {self.stock.complete_name, self.wh2.lot_stock_id.complete_name})
        w1 = by_name[self.stock.complete_name]
        w2 = by_name[self.wh2.lot_stock_id.complete_name]
        self._assert_row(w1, {'begin_qty': 10, 'begin_value': 100, 'in_qty': 6, 'out_qty': 0, 'int_qty': -3,
                              'int_value': -30, 'adj_qty': -2, 'adj_value': -20, 'end_qty': 11, 'end_value': 110})
        self._assert_row(w2, {'begin_qty': 0, 'in_qty': 0, 'out_qty': 1, 'out_value': 10, 'int_qty': 3,
                              'int_value': 30, 'adj_qty': 0, 'end_qty': 2, 'end_value': 20})
        for ln in (w1, w2):
            self.assertAlmostEqual(ln['begin_value'] + ln['in_value'] - ln['out_value'] + ln['int_value']
                                   + ln['adj_value'], ln['end_value'], places=2)
        comp = loc['compiled'][0]
        allx = comp['groups'][0]['lines'][0]
        self._assert_row(allx, {'begin_qty': 10, 'in_qty': 6, 'out_qty': 1, 'int_qty': 0, 'int_value': 0,
                                'adj_qty': -2, 'end_qty': 13, 'end_value': 130})
        self.assertEqual((comp['books_close_value'], comp['difference']), (130, 0))
        # a selected location only: one sheet, the shelf (sub-location of WH1/Stock)
        sel = self._report(product_ids=p, location_sheets=True, location_ids=self.shelf)
        self.assertEqual([sh['location_name'] for sh in sel['location_sheets']['sheets']], [self.shelf.complete_name])
        # location scope with no selection = all locations, one section each
        scope = self._report(product_ids=p, scope='location')
        self.assertEqual(len(scope['sections']), 2)
        # workbook: All Locations + one sheet per location, numeric cells, cached End values
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(InventoryValuationXlsx(self.env, ds).render()), data_only=True)
        self.assertEqual(wb.sheetnames[:2], ['Summary', 'All Locations'])
        self.assertEqual(len(wb.sheetnames), 2 + 2 + 4)
        wb1 = wb[self.stock.complete_name.replace('/', '-')[:31]]
        values = [c.value for row in wb1.iter_rows() for c in row if isinstance(c.value, (int, float))]
        self.assertIn(110, values)
        self.assertIn(-30, values)

    def test_19_simple_report_layout(self):
        """Simple report = the classic layout, one sheet/page per location, all locations by default."""
        import openpyxl
        p = self._product('SMP', self.cat_avco)
        self._in(p, 10, 10.0, '2026-09-20 10:00:00')
        self._in(p, 6, 10.0, '2026-10-01 10:00:00')
        self._move(p, 3, self.stock, self.wh2.lot_stock_id, '2026-10-03 10:00:00')
        self._out(p, 1, '2026-10-04 10:00:00', src=self.wh2.lot_stock_id)
        wiz = self._wizard(product_ids=p, simple_report=True)
        wiz.action_export_xlsx()
        self.assertTrue(wiz.file_name.startswith('Inventory_Valuation_Simple_'))
        wb = openpyxl.load_workbook(io.BytesIO(base64.b64decode(wiz.data)))
        self.assertEqual(wb.sheetnames, ['All Locations', self.stock.complete_name.replace('/', ''),
                                         self.wh2.lot_stock_id.complete_name.replace('/', '')])
        headers = ['Product', 'Costing', 'Begin Qty', 'Begin Value', 'In Qty', 'In Value', 'Out Qty', 'Out Value',
                   'Internal Qty', 'Internal Value', 'Adjust Qty', 'Adjust Value', 'End Qty', 'End Value']
        expected = {
            self.stock.complete_name: [10, 100, 6, 60, 0, 0, -3, -30, 0, 0, 13, 130],
            self.wh2.lot_stock_id.complete_name: [0, 0, 0, 0, 1, 10, 3, 30, 0, 0, 2, 20],
            'All Locations': [10, 100, 6, 60, 1, 10, 0, 0, 0, 0, 15, 150],
        }
        for ws in wb.worksheets:
            col_a = [ws.cell(r, 1).value for r in range(1, 5)]
            self.assertEqual(col_a[0], 'INVENTORY VALUATION REPORT')
            self.assertIn(col_a[1], expected)
            self.assertEqual(col_a[2], 'Company: %s' % self.company.name)
            self.assertEqual(col_a[3], 'Period: 2026-10-01 to 2026-10-31')
            self.assertEqual([ws.cell(5, c).value for c in range(1, 15)], headers)
            self.assertEqual([ws.cell(6, 1).value, ws.cell(6, 2).value], ['[SMP] Product SMP', 'average'])
            self.assertEqual([ws.cell(6, c).value for c in range(3, 15)], expected[col_a[1]])
            self.assertEqual(ws.cell(7, 1).value, 'GRAND TOTAL')
            self.assertEqual([ws.cell(7, c).value for c in range(3, 15)], expected[col_a[1]])
            self.assertEqual(ws.cell(6, 4).number_format, '#,##0.00')
        # selected location only: just that sheet
        one = self._wizard(product_ids=p, simple_report=True, location_ids=self.wh2.lot_stock_id)
        one.action_export_xlsx()
        wb = openpyxl.load_workbook(io.BytesIO(base64.b64decode(one.data)))
        self.assertEqual(len(wb.sheetnames), 1)
        # PDF: one page block per sheet, same figures
        html = self.env['ir.actions.report']._render_qweb_html(
            'eg_inventory_valuation_report.simple_valuation_report_action', wiz.ids)[0].decode()
        self.assertEqual(html.count('INVENTORY VALUATION REPORT'), 3)
        self.assertIn('All Locations', html)
        self.assertIn('150.00', html)
        action = wiz.action_print_pdf()
        self.assertIn('eg_inventory_valuation_report.simple_valuation_report', str(action))
        self.assertNotIn('stock_inventory_pdf_report', str(action))

    # ------------------------------------------------------------------
    # Accounting
    # ------------------------------------------------------------------
    def test_20_price_difference_from_vendor_bill(self):
        p = self._product('PDIFF', self.cat_auto_avco)
        with self._at('2026-10-01 10:00:00'):
            po = self.env['purchase.order'].create({
                'partner_id': self.partner_a.id,
                'order_line': [Command.create({'product_id': p.id, 'product_qty': 10, 'price_unit': 10.0})]})
            po.button_confirm()
            po.picking_ids.move_ids.quantity = 10
            po.picking_ids.move_ids.picked = True
            po.picking_ids.button_validate()
        with self._at('2026-10-05 10:00:00'):
            po.action_create_invoice()
            bill = po.invoice_ids
            bill.invoice_date = fields.Date.to_date('2026-10-05')
            bill.invoice_line_ids.price_unit = 12.0
            bill.action_post()
        ds = self._report(product_ids=p)
        self._assert_row(self._row(ds, p), {'in_value': 100, 'adj_value': 20, 'close_value': 120})
        self.assertIn('price_diff', {b['type'] for b in ds['breakdown']})

    def test_21_gl_reconciliation_reports_differences(self):
        p = self._product('GL', self.cat_auto_avco)
        self._in(p, 10, 10.0, '2026-10-01 10:00:00')
        self._out(p, 4, '2026-10-02 10:00:00')
        ds = self._report()
        gl = ds['reconciliation'][0]['gl']
        acc = self.company_data['default_account_stock_valuation']
        line = [g for g in gl if g['account'] == acc.display_name][0]
        self.assertEqual(line['inventory_value'], 60)
        self.assertTrue(line['ok'], line)
        # a manual entry on the stock account is reported, never absorbed
        move = self.env['account.move'].create({
            'date': '2026-10-20', 'journal_id': self.company_data['default_journal_misc'].id,
            'line_ids': [Command.create({'account_id': acc.id, 'debit': 25.0}),
                         Command.create({'account_id': self.company_data['default_account_expense'].id, 'credit': 25.0})]})
        move.action_post()
        ds = self._report()
        line = [g for g in ds['reconciliation'][0]['gl'] if g['account'] == acc.display_name][0]
        self.assertEqual((line['inventory_value'], line['gl_balance'], line['ok']), (60, 85, False))
        self.assertEqual(self._row(ds, p)['close_value'], 60)

    def test_22_accounting_date_basis(self):
        p = self._product('ACCD', self.cat_auto_avco)
        self._in(p, 10, 10.0, '2026-10-31 10:00:00')
        svl = self.env['stock.valuation.layer'].search([('product_id', '=', p.id)])
        self.assertTrue(svl.account_move_id)
        self.env.cr.execute('UPDATE account_move SET date=%s WHERE id=%s', ('2026-11-02', svl.account_move_id.id))
        self.env.invalidate_all()
        val = self._report(product_ids=p)
        self._assert_row(self._row(val, p), {'close_value': 100})
        acc = self._report(product_ids=p, date_basis='accounting')
        self.assertIsNone(self._row(acc, p))
        nov = self._report(product_ids=p, date_basis='accounting', start_date='2026-11-01', end_date='2026-11-30')
        self._assert_row(self._row(nov, p), {'open_value': 0, 'in_value': 100, 'close_value': 100})

    # ------------------------------------------------------------------
    # Dates / time zones
    # ------------------------------------------------------------------
    def test_30_timezone_day_boundaries(self):
        p = self._product('TZ', self.cat_avco)
        self._in(p, 1, 10.0, '2026-09-30 22:30:00')   # 01:30 on 1 Oct in Dar es Salaam (UTC+3)
        self._in(p, 1, 10.0, '2026-10-31 22:30:00')   # 01:30 on 1 Nov local
        wiz = self._wizard(product_ids=p).with_context(tz='Africa/Dar_es_Salaam')
        row = self._row(wiz._get_report_dataset(), p)
        self._assert_row(row, {'open_qty': 0, 'in_qty': 1, 'close_qty': 1})
        utc = self._report(product_ids=p)
        self._assert_row(self._row(utc, p), {'open_qty': 1, 'in_qty': 1, 'close_qty': 2})

    # ------------------------------------------------------------------
    # Multi-company & security
    # ------------------------------------------------------------------
    def test_40_multi_company_isolation_and_intercompany(self):
        self.env.ref('base.EUR').active = True
        data2 = self.setup_other_company(name='IVR Company 2', currency_id=self.env.ref('base.EUR').id)
        c2 = data2['company']
        self.env.user.company_ids |= c2
        wh_c2 = self.env['stock.warehouse'].search([('company_id', '=', c2.id)], limit=1)
        p = self._product('IC', self.cat_avco)   # shared product
        p.with_company(c2).categ_id.with_company(c2).property_cost_method = 'average'
        transit = self.env.ref('stock.stock_location_inter_company')
        self._in(p, 10, 10.0, '2026-10-01 10:00:00')
        self._move(p, 4, self.stock, transit, '2026-10-02 10:00:00')              # issue from company 1
        self._move(p, 4, transit, wh_c2.lot_stock_id, '2026-10-03 10:00:00', price=11.0, company=c2)
        ds1 = self._report(product_ids=p)
        self.assertEqual(len(ds1['sections']), 1)
        self._assert_row(self._row(ds1, p), {'in_qty': 10, 'out_qty': 4, 'close_qty': 6, 'close_value': 60})
        self.assertIn('transit_out', {b['type'] for b in ds1['breakdown']})
        both = self._report(product_ids=p, company_ids=self.company | c2)
        self.assertEqual(len(both['sections']), 2)
        rows = {s['company_id']: s['groups'][0]['rows'][0] for s in both['sections']}
        self._assert_row(rows[c2.id], {'in_qty': 4, 'close_qty': 4, 'close_value': 44})
        self.assertEqual(len(both['currency_totals']), 2, 'totals must never mix currencies')
        # a user restricted to company 1 cannot read company 2
        user = self.env['res.users'].create({
            'name': 'IVR manager C1', 'login': 'ivr_mgr_c1', 'company_id': self.company.id,
            'company_ids': [Command.set(self.company.ids)],
            'groups_id': [Command.set([self.env.ref('base.group_user').id,
                                       self.env.ref('stock.group_stock_manager').id])]})
        self.assertNotIn(c2, user.company_ids, 'test user must not have company 2: %s' % user.company_ids.mapped('name'))
        wiz = self.env['inventory.valuation.report'].with_user(user).create({
            'start_date': '2026-10-01', 'end_date': '2026-10-31', 'company_ids': [Command.set(c2.ids)]})
        self.assertEqual(wiz._get_companies(), c2, 'selected company must not be silently replaced')
        with self.assertRaises(AccessError):
            wiz._get_report_dataset()
        own = self.env['inventory.valuation.report'].with_user(user).create({
            'start_date': '2026-10-01', 'end_date': '2026-10-31', 'company_ids': [Command.set(self.company.ids)]})
        ds = own._get_report_dataset()
        self.assertEqual({s['company_id'] for s in ds['sections']}, {self.company.id})

    def test_41_requires_inventory_administrator(self):
        user = self.env['res.users'].create({
            'name': 'IVR stock user', 'login': 'ivr_stock_user', 'company_id': self.company.id,
            'company_ids': [Command.set(self.company.ids)],
            'groups_id': [Command.set([self.env.ref('base.group_user').id, self.env.ref('stock.group_stock_user').id])]})
        with self.assertRaises(AccessError):
            self.env['inventory.valuation.report'].with_user(user).create({'end_date': '2026-10-31'})
        with self.assertRaises(AccessError):
            self.env['eg.inventory.valuation.engine'].with_user(user)._build_dataset({
                'company_ids': self.company.ids, 'report_type': 'as_of', 'date_to': '2026-10-31', 'scope': 'company'})

    def test_42_parameter_validation(self):
        with self.assertRaises(Exception):
            self._wizard(start_date='2026-11-01', end_date='2026-10-01')
        # no location selected = all locations (no error)
        self.assertTrue(self._wizard(scope='location')._get_report_dataset())
        other = self.env['res.company'].create({'name': 'IVR other co'})
        other_loc = self.env['stock.location'].search([('company_id', '=', other.id), ('usage', '=', 'internal')], limit=1)
        if other_loc:
            with self.assertRaises(UserError):
                self._wizard(location_ids=other_loc)._get_report_dataset()

    # ------------------------------------------------------------------
    # Filters & edge cases
    # ------------------------------------------------------------------
    def test_50_filters_archived_zero_stock_cost_method(self):
        moved = self._product('MOVED', self.cat_avco)
        idle = self._product('IDLE', self.cat_avco)
        gone = self._product('GONE', self.cat_fifo)
        arch = self._product('ARCH', self.cat_std, cost=2.0)
        self._in(moved, 5, 10.0, '2026-10-01 10:00:00')
        self._in(gone, 5, 10.0, '2026-10-01 10:00:00')
        self._out(gone, 5, '2026-10-02 10:00:00')
        self._in(arch, 5, None, '2026-09-01 10:00:00')
        arch.active = False
        prods = moved | idle | gone | arch
        codes = lambda ds: {r['code'] for r in self._rows(ds).values()}  # noqa: E731
        self.assertEqual(codes(self._report(product_ids=prods)), {'MOVED', 'GONE', 'ARCH'})
        self.assertEqual(codes(self._report(product_ids=prods, stock_filter='nonzero')), {'MOVED', 'ARCH'})
        self.assertEqual(codes(self._report(product_ids=prods, stock_filter='all')), {'MOVED', 'IDLE', 'GONE', 'ARCH'})
        self.assertEqual(codes(self._report(product_ids=prods, include_archived=False)), {'MOVED', 'GONE'})
        self.assertEqual(codes(self._report(product_ids=prods, cost_method='fifo')), {'GONE'})
        self.assertEqual(codes(self._report(product_ids=prods, category_ids=self.cat_std)), {'ARCH'})
        arch_row = self._row_by(self._report(product_ids=prods), arch)
        self.assertIn('Archived product', arch_row['flags'])

    def test_51_empty_report_renders(self):
        ds = self._report(product_ids=self._product('NOTHING', self.cat_avco))
        self.assertFalse(self._rows(ds))
        content = InventoryValuationXlsx(self.env, ds).render()
        self.assertTrue(content.startswith(b'PK'))
        wiz = self._wizard(category_ids=self.cat_fifo)
        html = self.env['ir.actions.report']._render_qweb_html(
            'eg_inventory_valuation_report.stock_inventory_pdf_report_report', wiz.ids)[0]
        self.assertIn(b'Executive summary', html)

    def test_52_summary_level_and_no_grouping(self):
        a = self._product('S1', self.cat_avco)
        b = self._product('S2', self.cat_avco)
        self._in(a, 2, 5.0, '2026-10-01 10:00:00')
        self._in(b, 3, 5.0, '2026-10-01 10:00:00')
        ds = self._report(product_ids=a | b, detail_level='summary')
        self.assertEqual(ds['sections'][0]['groups'][0]['totals']['close_value'], 25)
        flat = self._report(product_ids=a | b, filter_by='product')
        self.assertEqual(len(flat['sections'][0]['groups']), 1)

    # ------------------------------------------------------------------
    # Export consistency
    # ------------------------------------------------------------------
    def test_60_pdf_and_excel_show_identical_figures(self):
        import openpyxl
        p1 = self._product('X1', self.cat_avco)
        p2 = self._product('X2', self.cat_fifo)
        self._in(p1, 10, 12.345, '2026-09-10 10:00:00')
        self._in(p1, 7, 13.10, '2026-10-02 10:00:00')
        self._out(p1, 3, '2026-10-03 10:00:00')
        self._in(p2, 4, 1.5, '2026-10-04 10:00:00')
        wiz = self._wizard(product_ids=p1 | p2)
        ds = wiz._get_report_dataset()
        wiz.action_export_xlsx()
        wb = openpyxl.load_workbook(io.BytesIO(base64.b64decode(wiz.data)), data_only=True)
        ws = wb['Valuation Detail']
        header = None
        found = {}
        for row in ws.iter_rows(values_only=False):
            values = [c.value for c in row]
            if 'Unit Cost' in values:
                header = values
                continue
            if header and values[header.index('Line Type')] == 'Product':
                code = values[header.index('Reference')]
                found[code] = {h: c for h, c in zip(header, row)}
        self.assertEqual(set(found), {'X1', 'X2'})
        rows = {r['code']: r for r in self._rows(ds).values()}
        for code, cells in found.items():
            r = rows[code]
            numeric = [c for c in cells.values() if isinstance(c.value, (int, float))]
            self.assertTrue(all(c.data_type == 'n' for c in numeric))
            values = [c.value for c in ws[cells['Reference'].row]]
            for key in ('open_qty', 'open_value', 'in_qty', 'in_value', 'out_qty', 'out_value', 'close_qty',
                        'close_value'):
                self.assertIn(r[key], values, '%s %s missing in Excel row' % (code, key))
        html = self.env['ir.actions.report']._render_qweb_html(
            'eg_inventory_valuation_report.stock_inventory_pdf_report_report', wiz.ids)[0].decode()
        for r in rows.values():
            self.assertIn('{:,.2f}'.format(r['close_value']), html)
        self.assertIn('{:,.2f}'.format(ds['sections'][0]['totals']['close_value']), html)
