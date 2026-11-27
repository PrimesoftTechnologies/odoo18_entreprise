# -*- coding: utf-8 -*-
"""Stock aging engine (Simple and Detailed modes).

One dataset feeds every export (PDF, Excel) of both modes.

Physical age — receipt-layer reconstruction
-------------------------------------------
All done stock move lines of the selected products that touch a valued
location of the selected companies (internal + company transit, consignment
excluded — same rule as the valuation report) are replayed in date order:

* a receipt from outside the company's valued locations (supplier,
  production, inventory gain, customer return, other company) creates an
  *age layer* dated at the receipt;
* an issue (customer, production, scrap, inventory loss, vendor return, other
  company) consumes layers of that location FIFO — or, for a lot/serial, the
  layers of that very lot first;
* an internal transfer moves the consumed layers to the destination location
  **with their original receipt dates** (a transfer never resets age);
* an issue larger than the available layers creates negative stock (no age),
  which the next receipts into that location fill first.

Value — never revalued
----------------------
The authoritative value is the company valuation from stock valuation layers
at the reporting date (same source as the Inventory Valuation Report).  It is
spread over the physical layers at the company unit cost (value / valued
quantity).  Aging therefore never applies FIFO costs to AVCO or Standard
products; it only tells *how old* the stock carrying that value is.  When the
physical quantity differs from the valued quantity the residual is reported
as "unallocated valuation", never hidden.
"""
from collections import defaultdict, deque
from datetime import datetime, time, timedelta

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools import float_round

EPS = 1e-9

KIND_LABELS = {
    'purchase': 'Purchase receipt',
    'production': 'Manufacturing output',
    'adjustment': 'Inventory adjustment',
    'return': 'Customer return',
    'interco': 'Inter-company / transit receipt',
    'other': 'Other receipt',
    'unknown': 'Unknown (transfer from negative stock)',
}
# How reliable the receipt date of a layer is
CONFIDENCE = {
    'purchase': 'FIFO estimate',
    'production': 'FIFO estimate',
    'adjustment': 'Estimated (count date)',
    'return': 'Return date',
    'interco': 'Company receipt date',
    'other': 'FIFO estimate',
    'unknown': 'Unknown',
}
RISK_LEVELS = [(70, 'High'), (40, 'Medium'), (20, 'Low'), (0, 'Healthy')]


class StockAgingEngine(models.AbstractModel):
    _name = 'eg.stock.aging.engine'
    _description = 'Stock Aging Reporting Engine'

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------
    @api.model
    def _build_dataset(self, params):
        val = self.env['eg.inventory.valuation.engine']
        val._check_engine_access()
        p = self._normalise(params)
        products = val._get_products({
            'companies': p['companies'], 'include_archived': p['include_archived'],
            'product_ids': p['product_ids'], 'category_ids': p['category_ids']})
        product_info = val._get_product_info(products)
        product_info = {k: v for k, v in product_info.items() if v['is_storable']}
        cat_info = val._get_category_info(products, p['companies'])
        if p['cost_method'] != 'all':
            product_info = {pid: info for pid, info in product_info.items()
                            if any(cat_info.get((c.id, info['categ_id']), {}).get('cost_method') == p['cost_method']
                                   for c in p['companies'])}
        locs = self._valued_locations(p)
        book = self._book_values(p, list(product_info))
        lots = {}
        sim = self._simulate(p, product_info, locs, lots)
        self._read_lots(lots)
        partners = self._read_partners(sim['partner_ids'])

        p['valuation_check'] = self._valuation_cross_check(p) if not p['lot_ids'] else {}
        p['quant_check'] = self._quant_cross_check(p, list(product_info), locs)
        companies = []
        for company in p['companies']:
            companies.append(self._company_dataset(p, company, product_info, cat_info, locs, book, sim, lots,
                                                   partners))
        return {
            'meta': self._meta(p, products),
            'mode': p['mode'],
            'buckets': p['bucket_labels'],
            'simple_buckets': p['simple_labels'],
            'companies': companies,
            'company_infos': [val._company_info(c) for c in p['companies']],
        }

    # ------------------------------------------------------------------
    # Parameters
    # ------------------------------------------------------------------
    def _normalise(self, params):
        p = dict(params)
        companies = self.env['res.company'].browse(p.get('company_ids') or []).exists()
        if not companies:
            raise UserError(_("Select at least one company."))
        if companies - self.env.user.company_ids:
            raise AccessError(_("You are not allowed to report on: %s",
                                ", ".join((companies - self.env.user.company_ids).mapped('name'))))
        p['companies'] = companies.sorted(lambda c: (c.sequence, c.name))
        try:
            tz = pytz.timezone(p.get('tz') or 'UTC')
        except pytz.UnknownTimeZoneError:
            tz = pytz.utc
        p['tz_obj'], p['tz'] = tz, tz.zone
        as_of = fields.Date.to_date(p.get('as_of') or fields.Date.context_today(self))
        p['as_of'] = as_of

        def to_utc(d):
            return tz.localize(datetime.combine(d, time.min)).astimezone(pytz.utc).replace(tzinfo=None)
        p['to_utc'] = to_utc
        p['end_utc'] = to_utc(as_of + timedelta(days=1))
        p['mode'] = p.get('mode') if p.get('mode') in ('simple', 'detailed') else 'simple'
        th = [int(x) for x in (p.get('thresholds') or [30, 60, 90, 180, 365])]
        if len(th) != 5 or any(t <= 0 for t in th) or th != sorted(set(th)):
            raise UserError(_("Aging thresholds must be five increasing numbers of days (e.g. 30, 60, 90, 180, 365)."))
        p['thresholds'] = th
        p['bucket_labels'] = ['0–%d Days' % th[0]] + ['%d–%d Days' % (th[i] + 1, th[i + 1]) for i in range(4)] + \
            ['Over %d Days' % th[4]]
        p['simple_thresholds'] = [30, 60, 90, 180]
        p['simple_labels'] = ['0–30 Days', '31–60 Days', '61–90 Days', '91–180 Days', 'Over 180 Days']
        for key, default in (('slow_days', 90), ('nonmoving_days', 180), ('analysis_days', 365),
                             ('expiry_days', 90), ('min_age_days', 0), ('top_n', 25), ('overstock_months', 12)):
            value = p.get(key)
            p[key] = max(int(value), 0) if value not in (None, False, '') else default
        p['top_n'] = p['top_n'] or 25
        p['analysis_days'] = max(p['analysis_days'], 30)
        if p['nonmoving_days'] < p['slow_days']:
            raise UserError(_("The non-moving threshold must be greater than or equal to the slow-moving threshold."))
        for key in ('warehouse_ids', 'location_ids', 'category_ids', 'product_ids', 'lot_ids'):
            p[key] = list(p.get(key) or [])
        p.setdefault('cost_method', 'all')
        p['include_archived'] = p.get('include_archived', True)
        p['include_negative'] = p.get('include_negative', True)
        p['include_zero'] = p.get('include_zero', False)
        p['window_start_utc'] = to_utc(as_of - timedelta(days=p['analysis_days'] - 1))
        return p

    def _valuation_cross_check(self, p):
        """Closing value per company from the Inventory Valuation Report engine (independent code path)."""
        ds = self.env['eg.inventory.valuation.engine']._build_dataset({
            'company_ids': p['companies'].ids, 'report_type': 'as_of', 'date_to': p['as_of'], 'tz': p['tz'],
            'date_basis': 'valuation', 'scope': 'company', 'product_ids': p['product_ids'],
            'category_ids': p['category_ids'], 'cost_method': p['cost_method'], 'valuation_type': 'all',
            'stock_filter': 'active', 'include_archived': p['include_archived'], 'group_by': 'none',
            'detail_level': 'detailed', 'location_sheets': False})
        return {s['company_id']: s['totals']['close_value'] for s in ds['sections']}

    def _quant_cross_check(self, p, product_ids, locs):
        """Physical quantity per (company, product) from stock.quant (current on-hand, a source independent
        of the move history).  Only meaningful when the report date is today."""
        if p['as_of'] < fields.Date.context_today(self) or not product_ids or p['lot_ids']:
            return None
        self.env['stock.quant'].flush_model()
        self.env.cr.execute("""
            SELECT l.company_id, q.product_id, SUM(q.quantity)
              FROM stock_quant q JOIN stock_location l ON l.id = q.location_id
              JOIN res_company rc ON rc.id = l.company_id
             WHERE q.location_id = ANY(%s) AND q.product_id = ANY(%s)
               AND (q.owner_id IS NULL OR q.owner_id = rc.partner_id)
          GROUP BY 1, 2""", (locs['ids'], product_ids))
        return {(c, pid): float(q) for c, pid, q in self.env.cr.fetchall()}

    @staticmethod
    def bucket_index(age, thresholds):
        for i, t in enumerate(thresholds):
            if age <= t:
                return i
        return len(thresholds)

    # ------------------------------------------------------------------
    # Locations, book values
    # ------------------------------------------------------------------
    def _valued_locations(self, p):
        """Valued locations of the selected companies and the reporting scope."""
        val = self.env['eg.inventory.valuation.engine']
        Location = self.env['stock.location'].with_context(active_test=False, allowed_company_ids=p['companies'].ids)
        domain = [('company_id', 'in', p['companies'].ids), '|', ('usage', '=', 'internal'),
                  ('usage', '=', 'transit')] + val._unvalued_location_domain()
        valued = Location.search(domain)
        info = {}
        for loc in valued:
            wh = loc.warehouse_id
            info[loc.id] = {'company_id': loc.company_id.id, 'warehouse_id': wh.id or 0,
                            'warehouse': wh.name or _('Outside warehouses (transit, etc.)'),
                            'location': loc.complete_name}
        if p['location_ids']:
            selected = Location.search([('id', 'in', p['location_ids']), ('company_id', 'in', p['companies'].ids)])
            if not selected:
                raise UserError(_("None of the selected locations belongs to the selected companies."))
            scope = set(Location.search([('id', 'child_of', selected.ids)] + domain).ids)
        elif p['warehouse_ids']:
            scope = {lid for lid, i in info.items() if i['warehouse_id'] in set(p['warehouse_ids'])}
        else:
            scope = set(info)
        return {'info': info, 'scope': scope, 'ids': list(info),
                'company_of': {lid: i['company_id'] for lid, i in info.items()}}

    def _book_values(self, p, product_ids):
        """Company valuation per (company, product) at the reporting date + unit cost."""
        res = {}
        if not product_ids:
            return res
        self.env['stock.valuation.layer'].flush_model()
        self.env.cr.execute("""
            SELECT company_id, product_id, SUM(quantity), SUM(value)
              FROM stock_valuation_layer
             WHERE company_id = ANY(%s) AND product_id = ANY(%s) AND create_date < %s
          GROUP BY 1, 2
        """, (p['companies'].ids, product_ids, p['end_utc']))
        for company_id, product_id, qty, value in self.env.cr.fetchall():
            res[(company_id, product_id)] = {'qty': float(qty or 0), 'value': float(value or 0)}
        unit = self.env['eg.inventory.valuation.engine']._company_avg_cost(p, product_ids, p['end_utc'])
        for key, u in unit.items():
            res.setdefault(key, {'qty': 0.0, 'value': 0.0})['unit'] = float(u)
        return res

    # ------------------------------------------------------------------
    # Receipt-layer simulation
    # ------------------------------------------------------------------
    def _simulate(self, p, product_info, locs, lots):
        """Replay done move lines; returns remaining layers, negative stock,
        last receipts and demand statistics."""
        Move = self.env['stock.move']
        has_unbuild = 'unbuild_id' in Move._fields and Move._fields['unbuild_id'].store
        unbuild_sql = "sm.unbuild_id IS NOT NULL" if has_unbuild else "FALSE"
        self.env['stock.move.line'].flush_model()
        Move.flush_model()
        loc_company = locs['company_of']
        loc_info = locs['info']
        layers = defaultdict(deque)          # loc -> deque of layers
        deficits = defaultdict(float)        # (loc, product) -> negative qty (positive number)
        last_receipt_wh = {}                 # (company, product, wh) -> (date, kind)
        last_receipt_co = {}                 # (company, product) -> date
        first_receipt_co = {}
        receipts_co = defaultdict(list)      # (company, product) -> [(date, ml_id)] (for transfer fallback)
        last_transfer_in_wh = {}             # (company, product, wh) -> date
        receipt_meta = {}                    # ml_id -> metadata
        demand = defaultdict(lambda: {'last_out': None, 'qty': 0.0, 'moves': set(), 'returns': 0.0})
        negative_events = defaultdict(int)
        partner_ids = set()
        product_ids = sorted(product_info)
        out_layers = []
        batch = 500
        for i in range(0, len(product_ids), batch):
            chunk = product_ids[i:i + batch]
            self.env.cr.execute("""
                SELECT ml.id, ml.product_id, ml.location_id, ml.location_dest_id, ml.quantity_product_uom,
                       ml.date, ml.lot_id, ml.move_id, COALESCE(sm.reference, sp.name, sm.name),
                       COALESCE(sp.partner_id, sm.partner_id), sl.usage, dl.usage, {unbuild}
                  FROM stock_move_line ml
                  JOIN stock_move sm ON sm.id = ml.move_id
                  JOIN res_company rc ON rc.id = ml.company_id
                  JOIN stock_location sl ON sl.id = ml.location_id
                  JOIN stock_location dl ON dl.id = ml.location_dest_id
                  LEFT JOIN stock_picking sp ON sp.id = ml.picking_id
                 WHERE ml.state = 'done' AND ml.product_id = ANY(%(products)s) AND ml.date < %(end)s
                   AND (ml.location_id = ANY(%(locs)s) OR ml.location_dest_id = ANY(%(locs)s))
                   AND (ml.owner_id IS NULL OR ml.owner_id = rc.partner_id)
              ORDER BY ml.product_id, ml.date, ml.id
            """.format(unbuild=unbuild_sql), {'products': chunk, 'end': p['end_utc'], 'locs': locs['ids']})
            for (ml_id, pid, src, dst, qty, date, lot_id, move_id, ref, partner_id, su, du,
                 is_unbuild) in self.env.cr.fetchall():
                qty = float(qty or 0)
                if qty <= EPS:
                    continue
                s_co, d_co = loc_company.get(src), loc_company.get(dst)
                if lot_id:
                    lots.setdefault(lot_id, None)
                taken, short = [], 0.0
                if s_co:
                    taken, short = self._consume(layers[(src, pid)], qty, lot_id)
                    if short > EPS:
                        deficits[(src, pid)] += short
                        negative_events[(s_co, pid)] += 1
                    # demand (genuine outbound only: customers, production consumption)
                    if not d_co and (du == 'customer' and su != 'supplier' or du == 'production' and not is_unbuild):
                        for key in ((s_co, pid), (s_co, pid, loc_info[src]['warehouse_id'])):
                            dm = demand[key]
                            dm['last_out'] = max(dm['last_out'] or date, date)
                            if date >= p['window_start_utc']:
                                dm['qty'] += qty
                                dm['moves'].add(move_id)
                if d_co:
                    wh = loc_info[dst]['warehouse_id']
                    if s_co == d_co:
                        # internal transfer: layers keep their receipt date
                        incoming = [(t, ch) for t, ch in taken]
                        if short > EPS:
                            incoming.append((short, [short, None, None, lot_id, 'unknown', date]))
                        # layer = [qty, receipt date, receipt line, lot, kind, arrival at this warehouse]
                        changes_wh = loc_info[src]['warehouse_id'] != wh
                        prev = last_transfer_in_wh.get((d_co, pid, wh))
                        if loc_info[src]['warehouse_id'] != wh:
                            last_transfer_in_wh[(d_co, pid, wh)] = max(prev or date, date)
                        remaining = self._fill_deficit(deficits, (dst, pid), sum(t for t, _c in incoming))
                        # the first `filled` units cover negative stock; keep the rest (oldest first)
                        filled = sum(t for t, _c in incoming) - remaining
                        for t, ch in incoming:
                            use = min(t, filled)
                            filled -= use
                            t -= use
                            if t > EPS:
                                layers[(dst, pid)].append([t, ch[1], ch[2], ch[3], ch[4],
                                                           date if changes_wh else ch[5]])
                    else:
                        kind = self._receipt_kind(su, du, s_co, d_co, is_unbuild)
                        receipt_meta[ml_id] = {'ref': ref or '', 'partner_id': partner_id, 'kind': kind,
                                               'qty': qty, 'date': date, 'move_id': move_id, 'lot_id': lot_id,
                                               'company_id': d_co, 'product_id': pid}
                        if partner_id:
                            partner_ids.add(partner_id)
                        rest = self._fill_deficit(deficits, (dst, pid), qty)
                        if rest > EPS:
                            layers[(dst, pid)].append([rest, date, ml_id, lot_id, kind, date])
                        if kind == 'return':
                            for key in ((d_co, pid), (d_co, pid, wh)):
                                if date >= p['window_start_utc']:
                                    demand[key]['returns'] += qty
                        last_receipt_wh[(d_co, pid, wh)] = (date, kind)
                        last_receipt_co[(d_co, pid)] = date
                        first_receipt_co.setdefault((d_co, pid), date)
                        receipts_co[(d_co, pid)].append((date, kind))
        for (loc, pid), queue in layers.items():
            for qty, date, ml_id, lot_id, kind, arrival in queue:
                if qty > EPS:
                    out_layers.append({'loc': loc, 'product_id': pid, 'qty': qty, 'date': date, 'ml_id': ml_id,
                                       'lot_id': lot_id, 'kind': kind, 'arrival': arrival})
        return {'layers': out_layers, 'deficits': {k: v for k, v in deficits.items() if v > EPS},
                'last_receipt_wh': last_receipt_wh, 'last_receipt_co': last_receipt_co,
                'first_receipt_co': first_receipt_co, 'receipts_co': receipts_co,
                'last_transfer_in_wh': last_transfer_in_wh, 'receipt_meta': receipt_meta, 'demand': demand,
                'negative_events': negative_events, 'partner_ids': partner_ids}

    @staticmethod
    def _consume(queue, qty, lot_id):
        """Take qty from a location's layers: the line's own lot first, then
        untracked layers, FIFO.  Returns ([(qty, layer)], shortfall)."""
        taken = []
        passes = (lot_id, None) if lot_id else (None,)
        for want in passes:
            i = 0
            while qty > EPS and i < len(queue):
                layer = queue[i]
                if lot_id and layer[3] != want:
                    i += 1
                    continue
                t = min(layer[0], qty)
                taken.append((t, list(layer)))
                layer[0] -= t
                qty -= t
                if layer[0] <= EPS:
                    del queue[i]
                else:
                    i += 1
            if qty <= EPS:
                break
        return taken, max(qty, 0.0)

    @staticmethod
    def _fill_deficit(deficits, key, qty):
        """Incoming quantity first covers negative stock at that location."""
        d = deficits.get(key, 0.0)
        if d > EPS:
            fill = min(d, qty)
            deficits[key] = d - fill
            qty -= fill
        return qty

    @staticmethod
    def _receipt_kind(su, du, s_co, d_co, is_unbuild):
        if s_co and s_co != d_co:
            return 'interco'
        return {'supplier': 'purchase', 'production': 'production', 'inventory': 'adjustment',
                'customer': 'return', 'transit': 'interco'}.get(su, 'other')

    def _read_lots(self, lots):
        if not lots:
            return
        Lot = self.env['stock.lot'].with_context(active_test=False)
        has_exp = 'expiration_date' in Lot._fields
        for lot in Lot.search([('id', 'in', list(lots))]):
            lots[lot.id] = {'name': lot.name, 'expiration_date': lot.expiration_date if has_exp else False}

    def _read_partners(self, partner_ids):
        if not partner_ids:
            return {}
        partners = self.env['res.partner'].with_context(active_test=False).search([('id', 'in', list(partner_ids))])
        return {pt.id: pt.display_name for pt in partners}

    # ------------------------------------------------------------------
    # Per company analytics
    # ------------------------------------------------------------------
    def _company_dataset(self, p, company, product_info, cat_info, locs, book, sim, lots, partners):
        cur = company.currency_id
        tz = p['tz_obj']
        as_of = p['as_of']
        th, sth = p['thresholds'], p['simple_thresholds']
        nb = len(th) + 1
        qd = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        loc_info = locs['info']

        cid = company.id
        _date_cache = {}

        def local_date(dt):
            if not dt:
                return None
            d = _date_cache.get(dt)
            if d is None:
                d = _date_cache[dt] = pytz.utc.localize(dt).astimezone(tz).date()
            return d
        # labels translated once per report (not once per layer)
        kind_labels = {k: _(v) for k, v in KIND_LABELS.items()}
        conf_labels = {k: _(v) for k, v in CONFIDENCE.items()}
        tracked_label = _('Tracked lot/serial')
        p['_labels'] = p.get('_labels') or {
            'status': {'none': _('No stock'), 'non_moving': _('Non-moving'), 'slow': _('Slow-moving'),
                       'new': _('Recently arrived'), 'moving': _('Moving')},
            'flags': {'negative': _('Negative stock'), 'unknown': _('Age unknown for part of the stock'),
                      'estimated': _('Age estimated from inventory adjustment'), 'archived': _('Archived product')},
        }
        flag_labels = p['_labels']['flags']

        def unit_of(pid):
            b = book.get((cid, pid))
            return b.get('unit', 0.0) if b else 0.0

        # ---- layers of this company ------------------------------------------------
        all_phys = defaultdict(float)        # product -> physical qty, all company locations
        layers = []
        for lay in sim['layers']:
            if locs['company_of'].get(lay['loc']) != cid or lay['product_id'] not in product_info:
                continue
            if p['lot_ids'] and lay['lot_id'] not in p['lot_ids']:
                continue
            all_phys[lay['product_id']] += lay['qty']
            info = loc_info[lay['loc']]
            rdate = local_date(lay['date'])
            age = (as_of - rdate).days if rdate else None
            unit = unit_of(lay['product_id'])
            meta = sim['receipt_meta'].get(lay['ml_id'], {})
            lot = lots.get(lay['lot_id']) or {}
            layers.append({
                'product_id': lay['product_id'], 'loc_id': lay['loc'], 'in_scope': lay['loc'] in locs['scope'],
                'warehouse_id': info['warehouse_id'], 'warehouse': info['warehouse'], 'location': info['location'],
                'lot': lot.get('name') or '', 'expiration_date': lot.get('expiration_date') or False,
                'receipt_ref': meta.get('ref', ''), 'receipt_date': rdate,
                'source': partners.get(meta.get('partner_id')) or kind_labels[lay['kind']],
                'kind': lay['kind'], 'kind_label': kind_labels[lay['kind']],
                'confidence': tracked_label if (lay['lot_id'] and lay['kind'] in ('purchase', 'production'))
                else conf_labels[lay['kind']],
                'ml_id': lay['ml_id'], 'move_id': meta.get('move_id'), 'original_qty': meta.get('qty'),
                'qty': lay['qty'], 'unit_cost': unit, 'value': lay['qty'] * unit,
                'age': age, 'bucket': self.bucket_index(age, th) if age is not None else None,
                'arrival': local_date(lay['arrival']),
                'simple_bucket': self.bucket_index(age, sth) if age is not None else None,
            })
        # consumed quantity of each receipt = original - everything still remaining from it
        remaining_by_receipt = defaultdict(float)
        for lay in layers:
            if lay['ml_id']:
                remaining_by_receipt[lay['ml_id']] += lay['qty']
        for lay in layers:
            if lay['ml_id'] and lay['original_qty'] is not None:
                lay['consumed_qty'] = max(lay['original_qty'] - remaining_by_receipt[lay['ml_id']], 0.0)
            else:
                lay['consumed_qty'] = None
        negatives = []
        for (loc, pid), qty in sim['deficits'].items():
            if locs['company_of'].get(loc) != cid or pid not in product_info or p['lot_ids']:
                continue
            all_phys[pid] -= qty
            info = loc_info[loc]
            negatives.append({'product_id': pid, 'loc_id': loc, 'in_scope': loc in locs['scope'],
                              'warehouse_id': info['warehouse_id'], 'warehouse': info['warehouse'],
                              'location': info['location'], 'qty': -qty, 'value': -qty * unit_of(pid)})

        # ---- product x warehouse rows (scope only) ---------------------------------
        def new_row(pid, wh_id, wh_name):
            info = product_info[pid]
            ci = cat_info.get((cid, info['categ_id']), {})
            return {'product_id': pid, 'code': info['code'], 'name': info['name'], 'categ': info['categ_name'],
                    'uom': info['uom'], 'uom_id': info['uom_id'], 'warehouse_id': wh_id, 'warehouse': wh_name,
                    'cost_method': ci.get('cost_method') or '', 'active': info['active'],
                    'qty': 0.0, 'value': 0.0, 'buckets': [0.0] * nb, 'bucket_qty': [0.0] * nb,
                    'simple_buckets': [0.0] * 5, 'unknown_value': 0.0, 'negative_qty': 0.0, 'negative_value': 0.0,
                    'age_value': 0.0, 'aged_value': 0.0, 'oldest': None, 'estimated_value': 0.0,
                    'unit_cost': unit_of(pid), 'locations': set(), 'arrival': None}
        rows = {}
        for lay in layers:
            if not lay['in_scope']:
                continue
            key = (lay['product_id'], lay['warehouse_id'])
            r = rows.get(key) or rows.setdefault(key, new_row(lay['product_id'], lay['warehouse_id'], lay['warehouse']))
            r['qty'] += lay['qty']
            r['value'] += lay['value']
            r['locations'].add(lay['location'])
            if lay['arrival'] and (r['arrival'] is None or lay['arrival'] < r['arrival']):
                r['arrival'] = lay['arrival']
            if lay['age'] is None:
                r['unknown_value'] += lay['value']
                continue
            r['buckets'][lay['bucket']] += lay['value']
            r['bucket_qty'][lay['bucket']] += lay['qty']
            r['age_value'] += lay['value'] * lay['age']
            if lay['age'] > th[2]:
                r['aged_value'] += lay['value']
            if lay['kind'] == 'adjustment':
                r['estimated_value'] += lay['value']
            if r['oldest'] is None or lay['receipt_date'] < r['oldest']:
                r['oldest'] = lay['receipt_date']
        for neg in negatives:
            if not neg['in_scope'] or not p['include_negative']:
                continue
            key = (neg['product_id'], neg['warehouse_id'])
            r = rows.get(key) or rows.setdefault(key, new_row(neg['product_id'], neg['warehouse_id'], neg['warehouse']))
            r['qty'] += neg['qty']
            r['value'] += neg['value']
            r['negative_qty'] += neg['qty']
            r['negative_value'] += neg['value']
            r['locations'].add(neg['location'])

        # demand / risk per row
        for (pid, wh_id), r in rows.items():
            # holding period = since the oldest stock now in this warehouse arrived here
            r['held_days'] = (as_of - r['arrival']).days if r['arrival'] else None
            self._row_metrics(p, r, sim['demand'].get((cid, pid, wh_id)), as_of, tz)
            lr = sim['last_receipt_wh'].get((cid, pid, wh_id))
            r['last_receipt_wh'] = local_date(lr[0]) if lr else None
            lr_co = sim['last_receipt_co'].get((cid, pid))
            r['last_receipt_co'] = local_date(lr_co) if lr_co else None
            r['locations'] = ', '.join(sorted(r['locations']))
            r['flags'] = []
            if r['negative_qty'] < -EPS:
                r['flags'].append(flag_labels['negative'])
            if r['unknown_value'] and abs(r['unknown_value']) > 0.005:
                r['flags'].append(flag_labels['unknown'])
            if r['estimated_value'] > 0.005:
                r['flags'].append(flag_labels['estimated'])
            if not r['active']:
                r['flags'].append(flag_labels['archived'])

        simple_rows = self._simple_rows(p, company, rows, sim, local_date, product_info, qd)
        result = {
            'company_id': company.id, 'company_name': company.name,
            'currency': self.env['eg.inventory.valuation.engine']._currency_info(cur),
            'simple_rows': simple_rows,
            'simple_totals': self._simple_totals(simple_rows, cur),
        }
        if p['mode'] == 'detailed':
            result.update(self._detailed(p, company, rows, layers, negatives, all_phys, book, sim, product_info,
                                         cat_info, local_date, cur, qd))
        result['reconciliation'] = self._reconcile(p, company, layers, negatives, all_phys, book, product_info,
                                                   cur, qd, simple_rows, result.get('rows_total_value'))
        return result

    def _row_metrics(self, p, r, dm, as_of, tz):
        """Demand, coverage, movement status and risk score of a product/warehouse row."""
        th = p['thresholds']
        last_out = pytz.utc.localize(dm['last_out']).astimezone(tz).date() if dm and dm['last_out'] else None
        out_qty = max((dm['qty'] - dm['returns']) if dm else 0.0, 0.0)
        r['last_out'] = last_out
        r['days_since_out'] = (as_of - last_out).days if last_out else None
        r['out_qty'] = out_qty
        r['out_moves'] = len(dm['moves']) if dm else 0
        oldest_age = (as_of - r['oldest']).days if r['oldest'] else 0
        r['oldest_age'] = oldest_age
        # Movement is judged over the period this warehouse has held the product
        # (stock transferred in last week cannot be "non-moving" here), while age
        # stays the receipt age carried by the layers.
        held = r.get('held_days')
        held = oldest_age if held is None else held
        r['held_days'] = held
        window_days = min(p['analysis_days'], max(held, 30))
        r['monthly'] = out_qty / (window_days / 30.4375) if out_qty > EPS else 0.0
        r['coverage'] = (r['qty'] / r['monthly']) if r['monthly'] > EPS and r['qty'] > 0 else None
        r['wavg_age'] = (r['age_value'] / (r['value'] - r['unknown_value'] - r['negative_value'])
                         if (r['value'] - r['unknown_value'] - r['negative_value']) > 0.005 else 0.0)
        no_recent_out = r['days_since_out'] is None or r['days_since_out'] > p['nonmoving_days']
        if r['qty'] <= EPS:
            status = 'none'
        elif no_recent_out and held >= p['nonmoving_days']:
            status = 'non_moving'
        elif (r['days_since_out'] is None or r['days_since_out'] > p['slow_days'] or
              (r['coverage'] or 0) > p['overstock_months']) and held >= p['slow_days']:
            status = 'slow'
        elif r['days_since_out'] is None and held < p['slow_days']:
            status = 'new'
        else:
            status = 'moving'
        r['status'] = status
        r['status_label'] = p['_labels']['status'][status]
        # potential dead stock: no demand for the non-moving period AND stock older than the 4th threshold
        r['dead'] = status == 'non_moving' and sum(r['buckets'][4:]) > 0.005
        # risk score (documented in the methodology)
        pos = max(r['value'] - r['negative_value'], 0.0)
        share = lambda lo: (sum(r['buckets'][lo:]) / pos) if pos > 0.005 else 0.0  # noqa: E731
        s_365, s_180, s_90 = share(5), share(4) - share(5), share(3) - share(4)
        age_pts = min(40.0, 40 * s_365 + 30 * s_180 + 15 * s_90)
        if r['qty'] <= EPS or status == 'new':
            move_pts = 0.0
        elif r['days_since_out'] is None:
            move_pts = 40.0 if held >= p['nonmoving_days'] else 20.0
        elif r['days_since_out'] > p['nonmoving_days']:
            move_pts = 35.0
        elif r['days_since_out'] > p['slow_days']:
            move_pts = 20.0
        else:
            move_pts = 0.0
        cov = r['coverage']
        if r['qty'] <= EPS or status == 'new':
            cov_pts = 0.0
        elif cov is None:
            cov_pts = 20.0
        elif cov > 2 * p['overstock_months']:
            cov_pts = 20.0
        elif cov > p['overstock_months']:
            cov_pts = 12.0
        elif cov > p['overstock_months'] / 2:
            cov_pts = 6.0
        else:
            cov_pts = 0.0
        score = round(min(100.0, age_pts + move_pts + cov_pts))
        r['risk_score'] = score
        r['risk'] = next(label for limit, label in RISK_LEVELS if score >= limit)
        r['risk_parts'] = (round(age_pts), round(move_pts), round(cov_pts))

    # ------------------------------------------------------------------
    # Simple mode
    # ------------------------------------------------------------------
    def _simple_rows(self, p, company, rows, sim, local_date, product_info, qd):
        """Simple report rows: product x warehouse, aged from the last receipt date."""
        out = []
        cid = company.id
        labels = {'transfer': _('Received via internal transfer: company receipt date used'),
                  'count': _('Last receipt is an inventory count: true receipt date unknown, stock may be older'),
                  'none': _('No receipt date found: age unknown'), 'negative': _('Negative stock'),
                  'no_stock': _('No stock')}
        for (pid, wh_id), r in rows.items():
            qty = float_round(r['qty'], precision_digits=qd)
            if not qty and not p['include_zero']:
                continue
            if qty < 0 and not p['include_negative']:
                continue
            remarks = []
            last = r['last_receipt_wh']
            lr = sim['last_receipt_wh'].get((cid, pid, wh_id))
            last_kind = lr[1] if lr else None
            if not last:
                # stock that only arrived through internal transfers: use the company's
                # latest receipt on or before that transfer (documented)
                t_in = sim['last_transfer_in_wh'].get((cid, pid, wh_id))
                cands = [rc for rc in sim['receipts_co'].get((cid, pid), []) if not t_in or rc[0] <= t_in]
                if cands:
                    best = max(cands, key=lambda rc: rc[0])
                    last, last_kind = local_date(best[0]), best[1]
                    remarks.append(labels['transfer'])
            if last_kind == 'adjustment':
                # never present a count date silently as a fresh receipt
                remarks.append(labels['count'])
            age = (p['as_of'] - last).days if last else None
            bucket = self.bucket_index(age, p['simple_thresholds']) if age is not None else None
            if last is None:
                remarks.append(labels['none'])
            if qty < 0:
                remarks.append(labels['negative'])
            out.append({
                'product_id': pid, 'code': r['code'], 'name': r['name'], 'categ': r['categ'],
                'warehouse': r['warehouse'], 'uom': r['uom'], 'uom_id': r['uom_id'], 'qty': qty,
                'unit_cost': r['unit_cost'], 'value': r['qty'] * r['unit_cost'],
                'last_receipt': last, 'age': age, 'bucket': bucket, 'remarks': '; '.join(remarks),
                'cost_method': r['cost_method'],
            })
        if p['include_zero']:
            seen = {o['product_id'] for o in out}
            for pid, info in product_info.items():
                if pid not in seen:
                    out.append({'product_id': pid, 'code': info['code'], 'name': info['name'],
                                'categ': info['categ_name'], 'warehouse': '', 'uom': info['uom'],
                                'uom_id': info['uom_id'], 'qty': 0.0, 'unit_cost': 0.0, 'value': 0.0,
                                'last_receipt': None, 'age': None, 'bucket': None, 'remarks': labels['no_stock'],
                                'cost_method': ''})
        out.sort(key=lambda o: (o['code'].lower(), o['name'].lower(), o['warehouse'].lower()))
        return out

    def _simple_totals(self, rows, cur):
        uniform = len({r['uom_id'] for r in rows}) <= 1
        tot = {'qty': sum(r['qty'] for r in rows) if uniform else None,
               'value': sum(r['value'] for r in rows),
               'buckets': [sum(r['value'] for r in rows if r['bucket'] == i) for i in range(5)],
               'unknown': sum(r['value'] for r in rows if r['bucket'] is None)}
        return tot

    # ------------------------------------------------------------------
    # Detailed mode analytics
    # ------------------------------------------------------------------
    def _detailed(self, p, company, rows, layers, negatives, all_phys, book, sim, product_info, cat_info,
                  local_date, cur, qd):
        th = p['thresholds']
        nb = len(th) + 1
        cid = company.id
        rlist = sorted(rows.values(), key=lambda r: -r['value'])
        total = sum(r['value'] for r in rlist)
        pos_total = sum(max(r['value'] - r['negative_value'], 0) for r in rlist)
        buckets = [sum(r['buckets'][i] for r in rlist) for i in range(nb)]
        bucket_qty_uniform = len({r['uom_id'] for r in rlist}) <= 1
        bucket_qty = [sum(r['bucket_qty'][i] for r in rlist) for i in range(nb)] if bucket_qty_uniform else None
        unknown = sum(r['unknown_value'] for r in rlist)
        negative = sum(r['negative_value'] for r in rlist)
        over = lambda idx: sum(buckets[idx:])  # noqa: E731
        known_value = sum(buckets)
        wavg_age = (sum(r['age_value'] for r in rlist) / known_value) if known_value > 0.005 else 0.0
        in_scope_layers = [lay for lay in layers if lay['in_scope']]
        oldest = min(in_scope_layers, key=lambda lay: (lay['receipt_date'] or p['as_of'])) if in_scope_layers else None
        slow_rows = [r for r in rlist if r['status'] in ('slow', 'non_moving')]
        dead_rows = [r for r in rlist if r['dead']]
        attention = [r for r in rlist if r['risk'] in ('High', 'Medium')]
        estimated = sum(r['estimated_value'] for r in rlist)

        # warehouses
        whs = {}
        for r in rlist:
            w = whs.setdefault(r['warehouse_id'], {'warehouse': r['warehouse'], 'value': 0.0, 'buckets': [0.0] * nb,
                                                   'age_value': 0.0, 'known': 0.0, 'dead': 0.0, 'slow': 0.0,
                                                   'products': 0, 'negative': 0.0})
            w['value'] += r['value']
            w['negative'] += r['negative_value']
            for i in range(nb):
                w['buckets'][i] += r['buckets'][i]
            w['age_value'] += r['age_value']
            w['known'] += sum(r['buckets'])
            w['dead'] += r['value'] if r['dead'] else 0.0
            w['slow'] += r['value'] if r['status'] in ('slow', 'non_moving') else 0.0
            w['products'] += 1 if r['qty'] > EPS else 0
        for w in whs.values():
            w['aged'] = sum(w['buckets'][3:])
            w['aged_pct'] = w['aged'] / w['known'] if w['known'] > 0.005 else 0.0
            w['wavg_age'] = w['age_value'] / w['known'] if w['known'] > 0.005 else 0.0
            w['share'] = w['value'] / total if total else 0.0
            w['shares'] = [b / w['known'] if w['known'] > 0.005 else 0.0 for b in w['buckets']]
        warehouses = sorted(whs.values(), key=lambda w: -w['value'])

        # categories
        cats = {}
        for r in rlist:
            c = cats.setdefault(r['categ'], {'categ': r['categ'] or _('Undefined'), 'value': 0.0, 'buckets': [0.0] * nb,
                                             'known': 0.0, 'age_value': 0.0, 'slow': 0.0, 'dead': 0.0, 'products': set()})
            c['value'] += r['value']
            for i in range(nb):
                c['buckets'][i] += r['buckets'][i]
            c['known'] += sum(r['buckets'])
            c['age_value'] += r['age_value']
            c['slow'] += r['value'] if r['status'] in ('slow', 'non_moving') else 0.0
            c['dead'] += r['value'] if r['dead'] else 0.0
            if r['qty'] > EPS:
                c['products'].add(r['product_id'])
        company_aged_pct = over(3) / known_value if known_value > 0.005 else 0.0
        for c in cats.values():
            c['products'] = len(c['products'])
            c['aged'] = sum(c['buckets'][3:])
            c['aged_pct'] = c['aged'] / c['known'] if c['known'] > 0.005 else 0.0
            c['slow_pct'] = c['slow'] / c['value'] if c['value'] > 0.005 else 0.0
            c['wavg_age'] = c['age_value'] / c['known'] if c['known'] > 0.005 else 0.0
            c['share'] = c['value'] / total if total else 0.0
        company_aged = over(3)
        company_dead = sum(r['value'] for r in dead_rows)
        for c in cats.values():
            # review: aged share above the company average with a material part of the aged
            # value, or a material part of the potential dead stock
            c['review'] = bool(
                (company_aged > 0.005 and c['aged_pct'] > company_aged_pct and c['aged'] >= 0.05 * company_aged)
                or (company_dead > 0.005 and c['dead'] >= 0.10 * company_dead))
        categories = sorted(cats.values(), key=lambda c: -c['value'])

        # product level (company) for capital exposure / replenishment
        prods = {}
        for r in rlist:
            pr = prods.setdefault(r['product_id'], {'product_id': r['product_id'], 'code': r['code'],
                                                    'name': r['name'], 'categ': r['categ'], 'uom': r['uom'],
                                                    'qty': 0.0, 'value': 0.0, 'buckets': [0.0] * nb,
                                                    'warehouses': [], 'aged_qty': 0.0})
            pr['qty'] += r['qty']
            pr['value'] += r['value']
            for i in range(nb):
                pr['buckets'][i] += r['buckets'][i]
            pr['aged_qty'] += sum(r['bucket_qty'][3:])
            if sum(r['buckets'][3:]) > 0.005:
                pr['warehouses'].append(r['warehouse'])
        for pr in prods.values():
            pr['aged'] = sum(pr['buckets'][3:])
            pr['over_180'] = sum(pr['buckets'][4:])
            pr['over_365'] = pr['buckets'][5]
            dm = sim['demand'].get((cid, pr['product_id']))
            out_qty = max((dm['qty'] - dm['returns']) if dm else 0.0, 0.0)
            first = sim['first_receipt_co'].get((cid, pr['product_id']))
            held = (p['as_of'] - local_date(first)).days if first else 0
            window = min(p['analysis_days'], max(held, 30))
            pr['monthly'] = out_qty / (window / 30.4375) if out_qty > EPS else 0.0
            pr['coverage'] = pr['qty'] / pr['monthly'] if pr['monthly'] > EPS and pr['qty'] > 0 else None
            last_out = dm['last_out'] if dm else None
            pr['last_out'] = local_date(last_out) if last_out else None
        products = sorted(prods.values(), key=lambda x: -x['value'])
        top_aged = sorted([x for x in products if x['aged'] > 0.005], key=lambda x: -x['aged'])

        # replenishment despite aged stock: a receipt within the first bucket while
        # stock older than the 3rd threshold (default 90 days) is still on hand
        recent_from = p['as_of'] - timedelta(days=th[0])
        replen = []
        recent = defaultdict(lambda: {'qty': 0.0, 'date': None, 'refs': set()})
        for meta in sim['receipt_meta'].values():
            if meta['company_id'] != cid or meta['kind'] not in ('purchase', 'production', 'interco'):
                continue
            d = local_date(meta['date'])
            if d >= recent_from:
                rc = recent[meta['product_id']]
                rc['qty'] += meta['qty']
                rc['date'] = max(rc['date'] or d, d)
                rc['refs'].add(meta['ref'])
        for pr in products:
            rc = recent.get(pr['product_id'])
            if rc and pr['aged'] > 0.005:
                unit = book.get((cid, pr['product_id']), {}).get('unit', 0.0)
                replen.append(dict(pr, recent_qty=rc['qty'], recent_date=rc['date'],
                                   recent_value=rc['qty'] * unit, recent_refs=', '.join(sorted(r for r in rc['refs'] if r))))
        replen.sort(key=lambda x: -x['aged'])

        # overstock (historical consumption)
        overstock = []
        for r in rlist:
            if r['coverage'] is not None and r['coverage'] > p['overstock_months'] and r['qty'] > 0:
                excess = r['qty'] - p['overstock_months'] * r['monthly']
                overstock.append(dict(r, excess_qty=excess, excess_value=excess * r['unit_cost']))
        overstock.sort(key=lambda x: -x['excess_value'])

        # expiry
        expiry = self._expiry(p, in_scope_layers, product_info)

        # concentration
        top10 = sum(x['value'] for x in products[:10])
        concentration = {
            'top10_value': top10, 'top10_share': top10 / total if total else 0.0,
            'products': len([x for x in products if x['qty'] > EPS]),
            'top_wh': warehouses[0] if warehouses else None,
            'top_cat': categories[0] if categories else None,
        }
        aged_wh_count = len([w for w in warehouses if sum(w['buckets'][4:]) > 0.005])
        kpis = {
            'total_value': total, 'products': len({r['product_id'] for r in rlist if r['qty'] > EPS}),
            'fresh': buckets[0], 'aging': buckets[1] + buckets[2], 'slow': sum(r['value'] for r in slow_rows),
            'dead': sum(r['value'] for r in dead_rows), 'over_90': over(3), 'over_180': over(4),
            'over_365': over(5), 'aged_pct': over(3) / known_value if known_value > 0.005 else 0.0,
            'wavg_age': wavg_age,
            'oldest_date': oldest['receipt_date'] if oldest else None,
            'oldest_product': (product_info[oldest['product_id']]['name'] if oldest else ''),
            'oldest_age': oldest['age'] if oldest else None,
            'attention': len({r['product_id'] for r in attention}),
            'aged_warehouses': aged_wh_count,
            'unreliable': unknown + estimated, 'unknown': unknown, 'estimated': estimated,
            'negative': negative, 'positive_total': pos_total,
        }
        min_age = p['min_age_days']
        listed_layers = [lay for lay in in_scope_layers if min_age <= 0 or (lay['age'] or 0) >= min_age]
        listed_layers.sort(key=lambda lay: (lay['receipt_date'] or p['as_of'], -lay['value']))
        result = {
            'kpis': kpis, 'buckets_value': buckets, 'buckets_qty': bucket_qty, 'unknown_value': unknown,
            'negative_value': negative, 'rows': rlist, 'rows_total_value': total,
            'warehouses': warehouses, 'categories': categories, 'products': products,
            'top_aged': top_aged, 'slow_rows': sorted(slow_rows, key=lambda r: -r['value']),
            'dead_rows': sorted(dead_rows, key=lambda r: -r['value']),
            'attention_rows': sorted(attention, key=lambda r: (-r['risk_score'], -r['value'])),
            'replenishment': replen, 'overstock': overstock, 'expiry': expiry,
            'layers': listed_layers, 'layer_count': len(in_scope_layers), 'concentration': concentration,
            'exposure': {'over_90': over(3), 'over_180': over(4), 'over_365': over(5)},
        }
        result['insights'] = self._insights(p, company, result, cur)
        return result

    def _expiry(self, p, layers, product_info):
        if 'expiration_date' not in self.env['stock.lot']._fields:
            return None
        end_dt = p['end_utc']
        warn = end_dt + timedelta(days=p['expiry_days'])
        out = []
        for lay in layers:
            exp = lay['expiration_date']
            if not exp:
                continue
            days = (pytz.utc.localize(exp).astimezone(p['tz_obj']).date() - p['as_of']).days
            status = 'expired' if exp < end_dt else ('expiring' if exp < warn else 'ok')
            info = product_info[lay['product_id']]
            out.append({'code': info['code'], 'name': info['name'], 'lot': lay['lot'], 'warehouse': lay['warehouse'],
                        'location': lay['location'], 'qty': lay['qty'], 'uom': info['uom'], 'value': lay['value'],
                        'expiration_date': pytz.utc.localize(exp).astimezone(p['tz_obj']).date(),
                        'days_left': days, 'status': status, 'age': lay['age']})
        out.sort(key=lambda x: (x['days_left'], -x['value']))
        return {
            'rows': out,
            'expired_value': sum(x['value'] for x in out if x['status'] == 'expired'),
            'expiring_value': sum(x['value'] for x in out if x['status'] == 'expiring'),
            'tracked_value': sum(x['value'] for x in out),
        }

    def _insights(self, p, company, d, cur):
        """Evidence-based findings, each with the numbers behind it."""
        fmt = lambda v: '{:,.2f} {}'.format(v, cur.name)  # noqa: E731
        k = d['kpis']
        th = p['thresholds']
        out = []
        total = k['total_value']
        if total <= 0.005:
            return [{'level': 'info', 'text': _("No positive stock value in scope at %s.", p['as_of'])}]
        if k['over_90'] > 0.005:
            out.append({'level': 'warning' if k['aged_pct'] > 0.3 else 'info', 'text': _(
                "%(pct).0f%% of inventory value (%(val)s) is older than %(d)s days; %(v180)s is older than %(d2)s days.",
                pct=k['aged_pct'] * 100, val=fmt(k['over_90']), d=th[2], v180=fmt(k['over_180']), d2=th[3])})
        aged_total = k['over_90']
        for w in d['warehouses'][:3]:
            if aged_total > 0.005 and w['aged'] / aged_total >= 0.5 and len(d['warehouses']) > 1:
                out.append({'level': 'warning', 'text': _(
                    "%(wh)s holds %(pct).0f%% of all inventory older than %(d)s days (%(val)s).",
                    wh=w['warehouse'], pct=w['aged'] / aged_total * 100, d=th[2], val=fmt(w['aged']))})
        if d['dead_rows']:
            top = d['dead_rows'][0]
            out.append({'level': 'danger', 'text': _(
                "%(n)s product/warehouse position(s) worth %(val)s show no customer or production demand for over "
                "%(nm)s days and hold stock older than %(d)s days. Largest: %(p)s at %(wh)s (%(v)s).",
                n=len(d['dead_rows']), val=fmt(k['dead']), nm=p['nonmoving_days'], d=th[3], p=top['name'],
                wh=top['warehouse'], v=fmt(top['value']))})
        if d['replenishment']:
            rv = sum(x['recent_value'] for x in d['replenishment'])
            av = sum(x['aged'] for x in d['replenishment'])
            out.append({'level': 'warning', 'text': _(
                "%(n)s product(s) were replenished in the last %(d)s days (%(rv)s received) while still holding "
                "%(av)s of stock older than %(d3)s days. Review purchasing for: %(names)s.",
                n=len(d['replenishment']), d=th[0], rv=fmt(rv), av=fmt(av), d3=th[2],
                names=', '.join(x['name'] for x in d['replenishment'][:3]))})
        slow_total = k['slow']
        for c in d['categories']:
            if slow_total > 0.005 and c['slow'] > 0.005 and c['share'] > 0:
                ratio = (c['slow'] / slow_total) / c['share']
                if ratio >= 1.5 and c['slow'] / slow_total >= 0.2:
                    out.append({'level': 'info', 'text': _(
                        "Category %(c)s holds %(s).0f%% of slow-moving value but only %(t).0f%% of total value.",
                        c=c['categ'], s=c['slow'] / slow_total * 100, t=c['share'] * 100)})
        # redistribution: non-moving in one warehouse, demand with < 1 month cover in another
        by_product = defaultdict(list)
        for r in d['rows']:
            by_product[r['product_id']].append(r)
        redis = 0
        for rows in by_product.values():
            idle = [r for r in rows if r['status'] in ('non_moving', 'slow') and r['qty'] > 0]
            short = [r for r in rows if r['monthly'] > EPS and (r['coverage'] or 0) < 1]
            if idle and short and redis < 3:
                redis += 1
                out.append({'level': 'info', 'text': _(
                    "%(p)s: %(q).2f %(u)s idle at %(a)s while %(b)s sells %(m).2f %(u)s/month with under one month "
                    "of cover — consider a transfer.", p=idle[0]['name'], q=idle[0]['qty'], u=idle[0]['uom'],
                    a=idle[0]['warehouse'], b=short[0]['warehouse'], m=short[0]['monthly'])})
        if k['unreliable'] > 0.005:
            out.append({'level': 'info', 'text': _(
                "%(val)s of stock has an estimated or unknown age (inventory adjustments or negative-stock "
                "corrections); verify physically before acting on its age.", val=fmt(k['unreliable']))})
        if k['negative'] < -0.005:
            out.append({'level': 'danger', 'text': _(
                "Negative stock worth %(val)s exists in scope: investigate missing receipts or posting errors.",
                val=fmt(k['negative']))})
        conc = d['concentration']
        if conc['top10_share'] >= 0.5 and conc['products'] > 10:
            out.append({'level': 'info', 'text': _(
                "The 10 largest products hold %(pct).0f%% of inventory value (%(val)s).",
                pct=conc['top10_share'] * 100, val=fmt(conc['top10_value']))})
        if not out:
            out.append({'level': 'success', 'text': _("No aged, slow-moving or exception positions were found.")})
        return out

    # ------------------------------------------------------------------
    # Reconciliation
    # ------------------------------------------------------------------
    def _reconcile(self, p, company, layers, negatives, all_phys, book, product_info, cur, qd, simple_rows,
                   detailed_total):
        rec = {'checks': [], 'exceptions': [], 'lines': []}
        cid = company.id
        pids = set(product_info)
        book_value = sum(b['value'] for (c, pid), b in book.items() if c == cid and pid in pids)
        all_value = sum(lay['value'] for lay in layers) + sum(n['value'] for n in negatives)
        scope_layers = sum(lay['value'] for lay in layers if lay['in_scope'])
        scope_neg = sum(n['value'] for n in negatives if n['in_scope'])
        if not p['include_negative']:
            scope_neg_excluded = scope_neg
            scope_neg = 0.0
        else:
            scope_neg_excluded = 0.0
        outside = all_value - scope_layers - sum(n['value'] for n in negatives if n['in_scope'])
        unallocated = book_value - all_value
        scope_value = scope_layers + scope_neg
        rec['lines'] = [
            {'label': _('Inventory value per Odoo books (valuation layers)'), 'value': book_value, 'kind': 'base'},
            {'label': _('Less: stock held outside the selected warehouses/locations'), 'value': -outside, 'kind': 'adj'},
            {'label': _('Less: valuation without matching physical quantity (unallocated)'), 'value': -unallocated,
             'kind': 'adj'},
            {'label': _('Less: negative stock excluded by filter'), 'value': -scope_neg_excluded, 'kind': 'adj'},
            {'label': _('= Stock value in this aging report'), 'value': scope_value, 'kind': 'total'},
        ]
        rec['book_value'], rec['scope_value'] = book_value, scope_value
        rec['outside'], rec['unallocated'] = outside, unallocated
        simple_total = sum(r['value'] for r in simple_rows)
        rec['simple_total'] = simple_total
        rec['checks'].append({'label': _('Simple report total = stock value in scope'),
                              'a': simple_total, 'b': scope_value, 'ok': cur.is_zero(simple_total - scope_value)})
        if detailed_total is not None:
            rec['checks'].append({'label': _('Detailed report total = Simple report total'),
                                  'a': detailed_total, 'b': simple_total, 'ok': cur.is_zero(detailed_total - simple_total)})
        full_scope = not (p['location_ids'] or p['warehouse_ids'] or p['lot_ids'])
        if cid in p.get('valuation_check', {}):
            ref = p['valuation_check'][cid]
            rec['checks'].append({'label': _('Book value = Inventory Valuation Report at the same date'),
                                  'a': book_value, 'b': ref, 'ok': cur.is_zero(book_value - ref)})
        if p.get('quant_check') is not None:
            q_phys = sum(v for pid, v in all_phys.items() if pid in pids)
            q_quant = sum(v for (c, pid), v in p['quant_check'].items() if c == cid and pid in pids)
            rec['checks'].append({'label': _('Reconstructed quantity = current on-hand (stock.quant)'),
                                  'a': q_phys, 'b': q_quant, 'ok': abs(q_phys - q_quant) < 10 ** -qd / 2,
                                  'is_qty': True})
        if full_scope:
            rec['checks'].append({'label': _('Unallocated valuation (should be 0)'), 'a': unallocated, 'b': 0.0,
                                  'ok': cur.is_zero(unallocated)})
        # quantity discrepancies per product (physical vs valued)
        for pid in sorted(pids):
            b = book.get((cid, pid), {'qty': 0.0, 'value': 0.0})
            phys = float_round(all_phys.get(pid, 0.0), precision_digits=qd)
            valued = float_round(b['qty'], precision_digits=qd)
            info = product_info[pid]
            if abs(phys - valued) > 10 ** -qd / 2:
                rec['exceptions'].append({'type': _('Quantity discrepancy'), 'code': info['code'], 'name': info['name'],
                                          'warehouse': '', 'qty': phys, 'value': phys * b.get('unit', 0.0),
                                          'detail': _('Physical %(p)s vs valued %(v)s %(u)s',
                                                      p=phys, v=valued, u=info['uom'])})
            residual = b['value'] - phys * b.get('unit', 0.0)
            if not cur.is_zero(residual):
                rec['exceptions'].append({'type': _('Unallocated valuation'), 'code': info['code'],
                                          'name': info['name'], 'warehouse': '', 'qty': 0.0, 'value': residual,
                                          'detail': _('Value not carried by physical stock (e.g. landed cost or '
                                                      'revaluation after the stock left, or a quantity discrepancy)')})
            if b['value'] and not b.get('unit') and phys:
                rec['exceptions'].append({'type': _('No unit cost'), 'code': info['code'], 'name': info['name'],
                                          'warehouse': '', 'qty': phys, 'value': 0.0,
                                          'detail': _('No valuation layer: stock carries no value')})
        for n in negatives:
            if n['in_scope']:
                info = product_info[n['product_id']]
                rec['exceptions'].append({'type': _('Negative stock'), 'code': info['code'], 'name': info['name'],
                                          'warehouse': n['warehouse'], 'qty': n['qty'], 'value': n['value'],
                                          'detail': n['location']})
        unknown = [lay for lay in layers if lay['in_scope'] and lay['age'] is None]
        for lay in unknown:
            info = product_info[lay['product_id']]
            rec['exceptions'].append({'type': _('Unknown age'), 'code': info['code'], 'name': info['name'],
                                      'warehouse': lay['warehouse'], 'qty': lay['qty'], 'value': lay['value'],
                                      'detail': _('Transferred while the source location was negative')})
        est = defaultdict(lambda: [0.0, 0.0])
        for lay in layers:
            if lay['in_scope'] and lay['kind'] == 'adjustment':
                k = (lay['product_id'], lay['warehouse'])
                est[k][0] += lay['qty']
                est[k][1] += lay['value']
        for (pid, wh), (q, v) in sorted(est.items(), key=lambda kv: -kv[1][1]):
            info = product_info[pid]
            rec['exceptions'].append({'type': _('Estimated age'), 'code': info['code'], 'name': info['name'],
                                      'warehouse': wh, 'qty': q, 'value': v,
                                      'detail': _('Stock added by inventory adjustment: dated at the count, true '
                                                  'receipt date unknown (opening balances)')})
        for r in simple_rows:
            if r['last_receipt'] is None and r['qty']:
                rec['exceptions'].append({'type': _('Missing receipt date (Simple)'), 'code': r['code'],
                                          'name': r['name'], 'warehouse': r['warehouse'], 'qty': r['qty'],
                                          'value': r['value'], 'detail': r['remarks']})
        rec['date_inconsistencies'] = self._date_inconsistencies(p, company, list(pids))
        for di in rec['date_inconsistencies']:
            rec['exceptions'].append({'type': _('Valuation date differs from move date'), 'code': di['code'],
                                      'name': di['name'], 'warehouse': '', 'qty': di['qty'], 'value': di['value'],
                                      'detail': _('%(ref)s: moved %(m)s, valued %(v)s', ref=di['ref'], m=di['move_date'],
                                                  v=di['svl_date'])})
        return rec

    def _date_inconsistencies(self, p, company, product_ids, limit=50):
        """Receipts whose valuation layer is dated more than one day apart from the stock move
        (back-dated moves or delayed validation): ages follow the move date, values the layer date."""
        if not product_ids:
            return []
        self.env.cr.execute("""
            SELECT pp.default_code, pt.name->>'en_US', sm.reference, sm.date, svl.create_date, svl.quantity, svl.value
              FROM stock_valuation_layer svl
              JOIN stock_move sm ON sm.id = svl.stock_move_id
              JOIN product_product pp ON pp.id = svl.product_id
              JOIN product_template pt ON pt.id = pp.product_tmpl_id
             WHERE svl.company_id = %s AND svl.product_id = ANY(%s) AND svl.quantity > 0
               AND svl.create_date < %s AND sm.date < %s
               AND abs(extract(epoch FROM (svl.create_date - sm.date))) > 86400
          ORDER BY svl.create_date DESC LIMIT %s
        """, (company.id, product_ids, p['end_utc'], p['end_utc'], limit))
        return [{'code': c or '', 'name': n or '', 'ref': r or '', 'move_date': md.date(), 'svl_date': sd.date(),
                 'qty': float(q), 'value': float(v)} for c, n, r, md, sd, q, v in self.env.cr.fetchall()]

    # ------------------------------------------------------------------
    def _meta(self, p, products):
        tz = p['tz_obj']
        now_local = pytz.utc.localize(fields.Datetime.now()).astimezone(tz)
        lang = self.env['res.lang']._get_data(code=self.env.user.lang or 'en_US')
        date_fmt = lang.date_format or '%m/%d/%Y'
        filters = [(_('Companies'), ', '.join(p['companies'].mapped('name'))),
                   (_('As at'), p['as_of'].strftime(date_fmt))]
        if p['warehouse_ids']:
            filters.append((_('Warehouses'), ', '.join(self.env['stock.warehouse'].browse(p['warehouse_ids']).mapped('name'))))
        if p['location_ids']:
            filters.append((_('Locations'), ', '.join(self.env['stock.location'].browse(p['location_ids']).mapped('complete_name'))))
        if not p['warehouse_ids'] and not p['location_ids']:
            filters.append((_('Locations'), _('All warehouses and locations')))
        if p['category_ids']:
            filters.append((_('Categories'), ', '.join(self.env['product.category'].browse(p['category_ids']).mapped('complete_name'))))
        if p['product_ids']:
            sel = self.env['product.product'].browse(p['product_ids']).with_context(active_test=False)
            filters.append((_('Products'), ', '.join(sel[:8].mapped('display_name')) + (' …' if len(sel) > 8 else '')))
        if p['lot_ids']:
            filters.append((_('Lots/Serials'), ', '.join(self.env['stock.lot'].browse(p['lot_ids']).mapped('name'))))
        if p['cost_method'] != 'all':
            filters.append((_('Costing method'), p['cost_method']))
        filters.append((_('Archived products'), _('Included') if p['include_archived'] else _('Excluded')))
        filters.append((_('Negative stock'), _('Included') if p['include_negative'] else _('Excluded')))
        if p['mode'] == 'detailed':
            filters.append((_('Aging buckets (days)'), ', '.join(str(t) for t in p['thresholds'])))
            filters.append((_('Slow / non-moving after'), _('%(s)s / %(n)s days without demand',
                                                             s=p['slow_days'], n=p['nonmoving_days'])))
            filters.append((_('Demand history'), _('%s days', p['analysis_days'])))
            if p['min_age_days']:
                filters.append((_('Detail lists show stock older than'), _('%s days', p['min_age_days'])))
        return {
            'title': _('Stock Aging Report'), 'mode': p['mode'], 'as_of': p['as_of'],
            'as_of_str': p['as_of'].strftime(date_fmt), 'generated_at': now_local.strftime(date_fmt + ' %H:%M'),
            'generated_by': self.env.user.name, 'tz': p['tz'], 'filters': filters,
            'thresholds': p['thresholds'], 'slow_days': p['slow_days'], 'nonmoving_days': p['nonmoving_days'],
            'analysis_days': p['analysis_days'], 'expiry_days': p['expiry_days'], 'top_n': p['top_n'],
            'overstock_months': p['overstock_months'],
            'qty_digits': self.env['decimal.precision'].precision_get('Product Unit of Measure'),
            'scope_filtered': bool(p['location_ids'] or p['warehouse_ids']),
        }
