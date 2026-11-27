# -*- coding: utf-8 -*-
"""Stock aging report tests.

Each scenario is dated relative to the report date (AS_OF) so ages are exact.
Every report is checked against figures calculated by hand in the test, an
independent SQL computation of physical quantities, the Inventory Valuation
engine, and the internal reconciliation identities.
"""
import base64
import io
from datetime import date, datetime, timedelta

from odoo import Command, fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import Form, tagged

from .common import IvrTestCommon

AS_OF = date(2026, 10, 31)


def ago(days, hour=10):
    """UTC timestamp `days` before AS_OF (user time zone is UTC in these tests)."""
    return (datetime.combine(AS_OF, datetime.min.time()) - timedelta(days=days) +
            timedelta(hours=hour)).strftime('%Y-%m-%d %H:%M:%S')


@tagged('post_install', '-at_install', 'inventory_valuation_report', 'stock_aging_report')
class TestStockAgingReport(IvrTestCommon):

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _aging_wizard(self, **kw):
        vals = {'as_of': AS_OF, 'simple_report': False, 'company_ids': [Command.set(self.company.ids)]}
        for key in ('product_ids', 'category_ids', 'location_ids', 'warehouse_ids', 'company_ids', 'lot_ids'):
            if key in kw and not isinstance(kw[key], list):
                kw[key] = [Command.set(kw[key].ids)]
        vals.update(kw)
        return self.env['stock.aging.report'].create(vals)

    def _aging(self, checks_ok=True, **kw):
        ds = self._aging_wizard(**kw)._get_report_dataset()
        for comp in ds['companies']:
            self._assert_aging_integrity(ds, comp, checks_ok)
        return ds

    def _assert_aging_integrity(self, ds, comp, checks_ok):
        cur = self.env['res.currency'].browse(comp['currency']['id'])
        # Simple rows: value = qty x unit cost; one bucket or unknown
        for r in comp['simple_rows']:
            self.assertAlmostEqual(r['value'], r['qty'] * r['unit_cost'], places=6)
        tot = comp['simple_totals']
        self.assertTrue(cur.is_zero(sum(tot['buckets']) + tot['unknown'] - tot['value']))
        if ds['mode'] == 'detailed':
            for r in comp['rows']:
                self.assertTrue(cur.is_zero(sum(r['buckets']) + r['unknown_value'] + r['negative_value'] - r['value']),
                                'row buckets %s' % r['name'])
            self.assertTrue(cur.is_zero(sum(comp['buckets_value']) + comp['unknown_value'] + comp['negative_value']
                                        - comp['kpis']['total_value']))
            # quantities: detailed rows == simple rows (same snapshot)
            dq = {(r['product_id'], r['warehouse']): r['qty'] for r in comp['rows']}
            for r in comp['simple_rows']:
                if r['warehouse']:
                    self.assertAlmostEqual(dq.get((r['product_id'], r['warehouse']), 0.0), r['qty'], places=4)
        if checks_ok:
            for chk in comp['reconciliation']['checks']:
                self.assertTrue(chk['ok'], 'reconciliation check failed: %s' % chk)

    def _sql_physical(self, product, company=None, as_of=AS_OF):
        """Independent physical quantity: done move lines into minus out of the company's valued locations."""
        company = company or self.company
        self.env.flush_all()
        self.env.cr.execute("""
            WITH v AS (SELECT id FROM stock_location WHERE company_id = %(c)s AND usage IN ('internal', 'transit'))
            SELECT COALESCE(SUM(CASE WHEN ml.location_dest_id IN (SELECT id FROM v) THEN ml.quantity_product_uom ELSE 0 END)
                          - SUM(CASE WHEN ml.location_id IN (SELECT id FROM v) THEN ml.quantity_product_uom ELSE 0 END), 0)
              FROM stock_move_line ml JOIN res_company rc ON rc.id = ml.company_id
             WHERE ml.state = 'done' AND ml.product_id = %(p)s AND ml.date < %(end)s
               AND (ml.owner_id IS NULL OR ml.owner_id = rc.partner_id)
        """, {'c': company.id, 'p': product.id, 'end': datetime.combine(as_of + timedelta(days=1), datetime.min.time())})
        return float(self.env.cr.fetchone()[0])

    def _valuation_close(self, products):
        """Closing value from the Inventory Valuation Report wizard (independent engine)."""
        wiz = self.env['inventory.valuation.report'].create({
            'report_type': 'as_of', 'end_date': AS_OF, 'company_ids': [Command.set(self.company.ids)],
            'product_ids': [Command.set(products.ids)]})
        return wiz._get_report_dataset()['sections'][0]['totals']['close_value']

    @staticmethod
    def _row(comp, product, warehouse=None):
        for r in comp['rows']:
            if r['product_id'] == product.id and (warehouse is None or r['warehouse'] == warehouse):
                return r
        return None

    @staticmethod
    def _srow(comp, product, warehouse=None):
        for r in comp['simple_rows']:
            if r['product_id'] == product.id and (warehouse is None or r['warehouse'] == warehouse):
                return r
        return None

    @staticmethod
    def _layers(comp, product):
        return sorted([(lay['age'], round(lay['qty'], 4)) for lay in comp['layers'] if lay['product_id'] == product.id],
                      key=lambda x: (x[0] is None, x[0] or 0))

    # ------------------------------------------------------------------
    # receipt-layer aging
    # ------------------------------------------------------------------
    def test_01_receipt_layers_vs_last_receipt(self):
        """100 units 200 days ago, 50 at 80 days, 30 at 10 days: the Detailed report splits them,
        the Simple report ages all 180 from the last receipt (10 days)."""
        p = self._product('AG1', self.cat_avco)
        self._in(p, 100, 10.0, ago(200))
        self._in(p, 50, 10.0, ago(80))
        self._in(p, 30, 10.0, ago(10))
        ds = self._aging(product_ids=p)
        comp = ds['companies'][0]
        self.assertEqual(self._layers(comp, p), [(10, 30), (80, 50), (200, 100)])
        r = self._row(comp, p)
        self.assertEqual([round(v, 2) for v in r['buckets']], [300, 0, 500, 0, 1000, 0])
        s = self._srow(comp, p)
        self.assertEqual((s['qty'], s['age'], s['bucket'], round(s['value'], 2)), (180, 10, 0, 1800))
        self.assertEqual(round(comp['simple_totals']['buckets'][0], 2), 1800)
        # partial consumption: selling 120 consumes the 100 oldest + 20 of the 80-day layer (FIFO)
        self._out(p, 120, ago(5))
        comp = self._aging(product_ids=p)['companies'][0]
        self.assertEqual(self._layers(comp, p), [(10, 30), (80, 30)])
        layer = [lay for lay in comp['layers'] if lay['age'] == 80][0]
        self.assertEqual((layer['original_qty'], layer['consumed_qty'], layer['qty']), (50, 20, 30))
        self.assertAlmostEqual(self._sql_physical(p), 60)

    def test_02_exact_bucket_boundaries(self):
        ages = [30, 31, 60, 61, 90, 91, 180, 181, 365, 366]
        prods = {}
        for a in ages:
            prods[a] = self._product('B%d' % a, self.cat_std, cost=1.0)
            self._in(prods[a], 1, None, ago(a))
        ds = self._aging(product_ids=self.env['product.product'].concat(*prods.values()))
        comp = ds['companies'][0]
        detailed = {a: self._row(comp, prods[a])['buckets'].index(1.0) for a in ages}
        self.assertEqual(detailed, {30: 0, 31: 1, 60: 1, 61: 2, 90: 2, 91: 3, 180: 3, 181: 4, 365: 4, 366: 5})
        simple = {a: self._srow(comp, prods[a])['bucket'] for a in ages}
        self.assertEqual(simple, {30: 0, 31: 1, 60: 1, 61: 2, 90: 2, 91: 3, 180: 3, 181: 4, 365: 4, 366: 4})
        self.assertEqual({a: self._srow(comp, prods[a])['age'] for a in ages}, {a: a for a in ages})

    def test_03_internal_transfer_keeps_age(self):
        p = self._product('AG3', self.cat_avco)
        self._in(p, 10, 10.0, ago(200))
        self._move(p, 4, self.stock, self.wh2.lot_stock_id, ago(5))
        self._move(p, 3, self.stock, self.shelf, ago(3))
        comp = self._aging(product_ids=p)['companies'][0]
        ages = {(lay['warehouse'], lay['location']): (lay['age'], lay['qty']) for lay in comp['layers']}
        self.assertEqual(ages[(self.wh2.name, self.wh2.lot_stock_id.complete_name)], (200, 4))
        self.assertEqual(ages[(self.wh.name, self.shelf.complete_name)], (200, 3))
        s2 = self._srow(comp, p, self.wh2.name)
        self.assertEqual((s2['age'], s2['qty']), (200, 4))
        self.assertIn('internal transfer', s2['remarks'])
        # warehouse filter: only WH2, outside stock explained in the reconciliation
        comp = self._aging(product_ids=p, warehouse_ids=self.wh2)['companies'][0]
        self.assertEqual(round(comp['reconciliation']['scope_value'], 2), 40)
        self.assertEqual(round(comp['reconciliation']['outside'], 2), 60)

    def test_04_historical_snapshot(self):
        p = self._product('AG4', self.cat_avco)
        self._in(p, 10, 10.0, ago(100))
        self._in(p, 10, 20.0, ago(-5))                      # after the report date
        comp = self._aging(product_ids=p)['companies'][0]
        r = self._row(comp, p)
        self.assertEqual((r['qty'], round(r['value'], 2), r['unit_cost']), (10, 100, 10))
        earlier = self._aging(product_ids=p, as_of=AS_OF - timedelta(days=150))['companies'][0]
        self.assertFalse(earlier['rows'])

    def test_05_costing_methods_never_revalue(self):
        """AVCO layers at 10 and 20 are both valued at the average 15; FIFO and Standard use the book unit cost."""
        avco = self._product('AGA', self.cat_avco)
        fifo = self._product('AGF', self.cat_fifo)
        std = self._product('AGS', self.cat_std, cost=8.0)
        for prod in (avco, fifo):
            self._in(prod, 10, 10.0, ago(200))
            self._in(prod, 10, 20.0, ago(20))
        self._in(std, 20, None, ago(120))
        comp = self._aging(product_ids=avco | fifo | std)['companies'][0]
        self.assertEqual({round(lay['unit_cost'], 4) for lay in comp['layers'] if lay['product_id'] == avco.id}, {15.0})
        ra, rf, rs = self._row(comp, avco), self._row(comp, fifo), self._row(comp, std)
        self.assertEqual([round(v, 2) for v in ra['buckets']], [150, 0, 0, 0, 150, 0])
        self.assertEqual(round(rf['value'], 2), 300)
        self.assertEqual(round(rs['value'], 2), 160)
        self.assertEqual(round(comp['kpis']['total_value'], 2), self._valuation_close(avco | fifo | std))

    def test_06_lots_and_expiry(self):
        p = self._product('AGL', self.cat_avco, tracking='lot')
        lot_a = self.env['stock.lot'].create({'name': 'LOT-A', 'product_id': p.id, 'company_id': self.company.id})
        lot_b = self.env['stock.lot'].create({'name': 'LOT-B', 'product_id': p.id, 'company_id': self.company.id})
        self._in(p, 5, 10.0, ago(300), lot=lot_a)
        self._in(p, 5, 10.0, ago(20), lot=lot_b)
        self._out(p, 3, ago(2), lot=lot_b)                   # sells the NEWER lot
        comp = self._aging(product_ids=p)['companies'][0]
        self.assertEqual({(lay['lot'], lay['age'], lay['qty']) for lay in comp['layers']},
                         {('LOT-A', 300, 5), ('LOT-B', 20, 2)})
        self.assertTrue(all(lay['confidence'] == 'Tracked lot/serial' for lay in comp['layers']))
        # lot filter
        only_a = self._aging(product_ids=p, lot_ids=lot_a)['companies'][0]
        self.assertEqual([(lay['lot'], lay['qty']) for lay in only_a['layers']], [('LOT-A', 5)])
        if 'expiration_date' in self.env['stock.lot']._fields:
            lot_a.expiration_date = datetime.combine(AS_OF - timedelta(days=10), datetime.min.time())
            lot_b.expiration_date = datetime.combine(AS_OF + timedelta(days=40), datetime.min.time())
            ex = self._aging(product_ids=p)['companies'][0]['expiry']
            self.assertEqual({(x['lot'], x['status'], x['days_left']) for x in ex['rows']},
                             {('LOT-A', 'expired', -10), ('LOT-B', 'expiring', 40)})
            self.assertEqual(round(ex['expired_value'], 2), 50)

    def test_07_returns_scrap_adjustment_opening(self):
        p = self._product('AG7', self.cat_avco)
        with self._at(ago(400)):                              # opening balance by inventory count
            quant = self.env['stock.quant'].with_context(inventory_mode=True).create({
                'product_id': p.id, 'location_id': self.stock.id, 'inventory_quantity': 10})
            quant.action_apply_inventory()
        self._in(p, 10, 10.0, ago(100))
        out = self._out(p, 12, ago(50))                       # consumes 10 opening + 2 of the receipt
        self._move(p, 2, self.customer, self.stock, ago(30), origin_move=out)   # customer return
        with self._at(ago(20)):
            self.env['stock.scrap'].create({'product_id': p.id, 'scrap_qty': 1, 'location_id': self.stock.id,
                                            'company_id': self.company.id}).action_validate()
        self._move(p, 1, self.stock, self.supplier, ago(10))  # vendor return
        comp = self._aging(product_ids=p)['companies'][0]
        # remaining: 8 from the 100-day receipt minus scrap 1 minus vendor return 1 (FIFO) = 6, + 2 returned
        self.assertEqual(self._layers(comp, p), [(30, 2), (100, 6)])
        self.assertEqual({lay['kind'] for lay in comp['layers']}, {'purchase', 'return'})
        self.assertAlmostEqual(self._sql_physical(p), 8)
        # demand = 12 delivered - 2 returned; scrap and vendor returns are not demand
        r = self._row(comp, p)
        self.assertEqual((r['out_qty'], r['last_out']), (10, AS_OF - timedelta(days=50)))
        # opening stock still on hand is flagged as estimated
        q = self._product('AG7B', self.cat_avco)
        with self._at(ago(500)):
            quant = self.env['stock.quant'].with_context(inventory_mode=True).create({
                'product_id': q.id, 'location_id': self.stock.id, 'inventory_quantity': 4})
            quant.action_apply_inventory()
        comp = self._aging(product_ids=q, checks_ok=False)['companies'][0]
        self.assertEqual(comp['layers'][0]['confidence'], 'Estimated (count date)')
        self.assertIn('inventory count', self._srow(comp, q)['remarks'])
        self.assertIn('Estimated age', [e['type'] for e in comp['reconciliation']['exceptions']])

    def test_08_negative_stock_and_unknown_age(self):
        p = self._product('AG8', self.cat_avco, cost=10.0)
        self._out(p, 5, ago(60))                              # negative stock
        comp = self._aging(product_ids=p, checks_ok=False)['companies'][0]
        r = self._row(comp, p)
        self.assertEqual((r['qty'], r['negative_qty']), (-5, -5))
        self.assertIn('Negative stock', [e['type'] for e in comp['reconciliation']['exceptions']])
        no_neg = self._aging(product_ids=p, include_negative=False, checks_ok=False)['companies'][0]
        self.assertFalse(no_neg['simple_rows'])
        self._in(p, 8, 10.0, ago(40))                         # fills the deficit first: 3 remain, aged 40
        comp = self._aging(product_ids=p)['companies'][0]
        self.assertEqual(self._layers(comp, p), [(40, 3)])
        # stock transferred out of a negative location has no known age
        q = self._product('AG8B', self.cat_avco, cost=10.0)
        self._move(q, 2, self.stock, self.wh2.lot_stock_id, ago(30))
        comp = self._aging(product_ids=q, checks_ok=False)['companies'][0]
        unknown = [lay for lay in comp['layers'] if lay['age'] is None]
        self.assertEqual(len(unknown), 1)
        s = self._srow(comp, q, self.wh2.name)
        self.assertIsNone(s['bucket'])
        self.assertIn('No receipt date', s['remarks'])

    def test_09_manufacturing_and_landed_costs(self):
        if 'mrp.production' not in self.env:
            self.skipTest('mrp not installed')
        comp_p = self._product('AGC', self.cat_avco)
        fin = self._product('AGF2', self.cat_avco)
        bom = self.env['mrp.bom'].create({'product_tmpl_id': fin.product_tmpl_id.id, 'product_qty': 1,
                                          'bom_line_ids': [Command.create({'product_id': comp_p.id, 'product_qty': 2})]})
        self._in(comp_p, 10, 4.0, ago(150))
        with self._at(ago(15)):
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
        comp = self._aging(product_ids=comp_p | fin)['companies'][0]
        self.assertEqual(self._layers(comp, fin), [(15, 3)])
        self.assertEqual(comp['layers'][[lay['product_id'] for lay in comp['layers']].index(fin.id)]['kind'], 'production')
        self.assertEqual(self._layers(comp, comp_p), [(150, 4)])
        self.assertEqual(self._row(comp, comp_p)['out_qty'], 6)      # consumption is demand
        if 'stock.landed.cost' in self.env:
            p = self._product('AGLC', self.stock_account_product_categ)
            freight = self.env['product.product'].create({'name': 'Freight', 'type': 'service', 'landed_cost_ok': True})
            with self._at(ago(60)):
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
            with self._at(ago(55)):
                lc = self.env['stock.landed.cost'].create({
                    'picking_ids': [Command.set(picking.ids)],
                    'account_journal_id': self.company_data['default_journal_misc'].id,
                    'cost_lines': [Command.create({'name': 'Freight', 'product_id': freight.id, 'price_unit': 50.0,
                                                   'split_method': 'equal',
                                                   'account_id': self.company_data['default_account_expense'].id})]})
                lc.compute_landed_cost()
                lc.button_validate()
            comp = self._aging(product_ids=p)['companies'][0]
            lay = comp['layers'][0]
            self.assertEqual((lay['age'], lay['qty'], round(lay['value'], 2)), (60, 10, 150))

    def test_10_intercompany_and_multi_currency(self):
        self.env.ref('base.EUR').active = True
        data2 = self.setup_other_company(name='IVR Aging Co 2', currency_id=self.env.ref('base.EUR').id)
        c2 = data2['company']
        self.env.user.company_ids |= c2
        wh_c2 = self.env['stock.warehouse'].search([('company_id', '=', c2.id)], limit=1)
        p = self._product('AGIC', self.cat_avco)
        p.categ_id.with_company(c2).property_cost_method = 'average'
        transit = self.env.ref('stock.stock_location_inter_company')
        self._in(p, 10, 10.0, ago(200))
        self._move(p, 4, self.stock, transit, ago(20))
        self._move(p, 4, transit, wh_c2.lot_stock_id, ago(18), price=11.0, company=c2)
        ds = self._aging(product_ids=p, company_ids=self.company | c2)
        comps = {c['company_id']: c for c in ds['companies']}
        self.assertEqual(self._layers(comps[self.company.id], p), [(200, 6)])
        self.assertEqual(self._layers(comps[c2.id], p), [(18, 4)])
        self.assertEqual(comps[c2.id]['layers'][0]['kind'], 'interco')
        self.assertEqual(comps[c2.id]['currency']['name'], 'EUR')
        self.assertEqual(round(comps[c2.id]['kpis']['total_value'], 2), 44)
        # companies whose names share a long prefix must still get distinct sheets (found on real data)
        self.company.name = 'Same Prefix Company (San Francisco)'
        c2.name = 'Same Prefix Company (Chicago)'
        import openpyxl
        for simple in (True, False):
            wiz = self._aging_wizard(product_ids=p, company_ids=self.company | c2, simple_report=simple)
            wiz.action_export_xlsx()
            names = openpyxl.load_workbook(io.BytesIO(base64.b64decode(wiz.data))).sheetnames
            self.assertEqual(len(names), len(set(n.lower() for n in names)))
            if simple:
                self.assertEqual(len(names), 5)

    # ------------------------------------------------------------------
    # demand, dead stock, risk
    # ------------------------------------------------------------------
    def test_20_demand_slow_dead_and_replenishment(self):
        dead = self._product('DEAD', self.cat_avco)
        self._in(dead, 20, 10.0, ago(400))
        self._out(dead, 5, ago(300))                          # no demand for 300 days
        moving = self._product('MOVE', self.cat_avco)
        self._in(moving, 100, 5.0, ago(200))
        for d in (60, 30, 10):
            self._out(moving, 10, ago(d))
        new = self._product('NEW', self.cat_avco)
        self._in(new, 10, 5.0, ago(5))
        replen = self._product('REPL', self.cat_avco)
        self._in(replen, 10, 5.0, ago(200))
        self._in(replen, 10, 5.0, ago(10))                    # replenished despite 200-day stock
        comp = self._aging(product_ids=dead | moving | new | replen)['companies'][0]
        rd, rm, rn = self._row(comp, dead), self._row(comp, moving), self._row(comp, new)
        self.assertEqual((rd['status'], rd['dead'], rd['days_since_out'], rd['risk']), ('non_moving', True, 300, 'High'))
        self.assertEqual(rd['risk_score'], 40 + 35 + 20)      # all > 365 d, no demand > 180 d, no recent demand
        # sold 10 days ago, but 70 units = 15.3 months of cover > 12: slow-moving (overstock), not dead
        self.assertEqual(rm['status'], 'slow')
        self.assertFalse(rm['dead'])
        # 30 units over 200 days held (window = 200 days) -> 4.565 per month; 70 on hand -> 15.3 months
        self.assertAlmostEqual(rm['monthly'], 30 / (200 / 30.4375), places=4)
        self.assertAlmostEqual(rm['coverage'], 70 / rm['monthly'], places=4)
        self.assertEqual((rn['status'], rn['risk_score'], rn['coverage']), ('new', 0, None))
        self.assertEqual([x['code'] for x in comp['replenishment']], ['REPL'])
        # REPL never sold in 200 days: also potential dead stock, although just replenished
        self.assertEqual(sorted(r['code'] for r in comp['dead_rows']), ['DEAD', 'REPL'])
        self.assertEqual(round(comp['kpis']['dead'], 2), 150 + 100)
        self.assertTrue(any('replenished' in i['text'] for i in comp['insights']))
        self.assertIn('MOVE', [o['code'] for o in comp['overstock']])

    def test_21_transferred_stock_keeps_age_but_not_idle_status(self):
        """Stock received 300 days ago and moved to WH2 10 days ago is 300 days old, but WH2 has only
        held it for 10 days: it is 'recently arrived' there, not non-moving or dead."""
        p = self._product('HOLD', self.cat_avco)
        self._in(p, 50, 10.0, ago(300))
        for d in (200, 100, 20):
            self._out(p, 5, ago(d))
        self._move(p, 10, self.stock, self.wh2.lot_stock_id, ago(10))
        comp = self._aging(product_ids=p)['companies'][0]
        r2 = self._row(comp, p, self.wh2.name)
        self.assertEqual((r2['oldest_age'], r2['held_days'], r2['status'], r2['dead']), (300, 10, 'new', False))
        self.assertEqual(r2['risk_parts'][1:], (0, 0))
        r1 = self._row(comp, p, self.wh.name)
        self.assertEqual((r1['held_days'], r1['status']), (300, 'slow'))     # 25 units vs 15 sold / 300 d

    # ------------------------------------------------------------------
    # filters, security, exports
    # ------------------------------------------------------------------
    def test_30_filters_zero_archived(self):
        a = self._product('F1', self.cat_avco)
        b = self._product('F2', self.cat_fifo)
        z = self._product('F3', self.cat_avco)
        self._in(a, 5, 10.0, ago(50))
        self._in(b, 5, 10.0, ago(50))
        b.active = False
        prods = a | b | z
        codes = lambda ds: sorted(r['code'] for r in ds['companies'][0]['simple_rows'])  # noqa: E731
        self.assertEqual(codes(self._aging(product_ids=prods, simple_report=True)), ['F1', 'F2'])
        self.assertEqual(codes(self._aging(product_ids=prods, simple_report=True, include_archived=False)), ['F1'])
        self.assertEqual(codes(self._aging(product_ids=prods, simple_report=True, include_zero=True)), ['F1', 'F2', 'F3'])
        self.assertEqual(codes(self._aging(product_ids=prods, simple_report=True, cost_method='fifo')), ['F2'])

    def test_31_security(self):
        user = self.env['res.users'].create({
            'name': 'aging stock user', 'login': 'aging_stock_user', 'company_id': self.company.id,
            'company_ids': [Command.set(self.company.ids)],
            'groups_id': [Command.set([self.env.ref('base.group_user').id, self.env.ref('stock.group_stock_user').id])]})
        with self.assertRaises(AccessError):
            self.env['stock.aging.report'].with_user(user).create({'as_of': AS_OF})
        other = self.env['res.company'].create({'name': 'Aging other co'})
        mgr = self.env['res.users'].create({
            'name': 'aging mgr', 'login': 'aging_mgr', 'company_id': self.company.id,
            'company_ids': [Command.set(self.company.ids)],
            'groups_id': [Command.set([self.env.ref('base.group_user').id, self.env.ref('stock.group_stock_manager').id])]})
        wiz = self.env['stock.aging.report'].with_user(mgr).create({'as_of': AS_OF, 'company_ids': [Command.set(other.ids)]})
        with self.assertRaises(AccessError):
            wiz._get_report_dataset()
        with self.assertRaises(Exception):
            self._aging_wizard(bucket_2=10)

    def test_40_exports_identical_figures(self):
        import openpyxl
        p = self._product('EX1', self.cat_avco)
        q = self._product('EX2', self.cat_fifo)
        self._in(p, 7, 12.345, ago(250))
        self._in(p, 3, 13.1, ago(20))
        self._in(q, 4, 1.5, ago(45))
        self._out(p, 2, ago(100))
        for simple in (True, False):
            wiz = self._aging_wizard(product_ids=p | q, simple_report=simple)
            ds = wiz._get_report_dataset()
            comp = ds['companies'][0]
            wiz.action_export_xlsx()
            wb = openpyxl.load_workbook(io.BytesIO(base64.b64decode(wiz.data)), data_only=True)
            xmlid = 'eg_inventory_valuation_report.action_aging_%s' % ('simple' if simple else 'detailed')
            html = self.env['ir.actions.report']._render_qweb_html(xmlid, wiz.ids)[0].decode()
            total = comp['simple_totals']['value']
            self.assertIn('{:,.2f}'.format(total), html)
            if simple:
                ws = wb['Stock Aging']
                self.assertEqual([ws.cell(4, c).value for c in range(1, 15)], [
                    'Item Code', 'Item Description', 'Category', 'Warehouse', 'Quantity on Hand',
                    'Unit Cost (%s)' % comp['currency']['name'], 'Stock Value (%s)' % comp['currency']['name'],
                    'Last Receipt Date', 'Age (Days)', '0–30 Days', '31–60 Days', '61–90 Days', '91–180 Days',
                    'Over 180 Days'])
                self.assertEqual(wb.sheetnames, ['Stock Aging', 'Aging Summary', 'Instructions'])
                total_row = 5 + len(comp['simple_rows'])
                self.assertEqual(ws.cell(total_row, 2).value, 'TOTAL')
                self.assertAlmostEqual(ws.cell(total_row, 7).value, total, places=6)
                self.assertEqual(ws['B2'].value.date(), AS_OF)
                self.assertAlmostEqual(wb['Aging Summary']['B9'].value, total, places=6)
            else:
                self.assertIn('Executive Summary', wb.sheetnames)
                self.assertIn('Reconciliation & Exceptions', wb.sheetnames)
                ws = wb['Aging Overview']
                values = [c.value for row in ws.iter_rows() for c in row if isinstance(c.value, (int, float))]
                self.assertTrue(any(abs(v - comp['kpis']['total_value']) < 1e-6 for v in values))

    def test_41_valuation_report_regression(self):
        """The valuation wizard keeps working with the aging feature installed."""
        p = self._product('REG', self.cat_avco)
        self._in(p, 5, 10.0, ago(20))
        self.assertEqual(self._valuation_close(p), 50)
        menu_val = self.env.ref('eg_inventory_valuation_report.import_inventory_valuation_report_wizard')
        menu_age = self.env.ref('eg_inventory_valuation_report.menu_stock_aging_report')
        self.assertEqual(menu_age.parent_id, menu_val.parent_id)
        self.assertEqual(menu_age.sequence, menu_val.sequence + 1)
