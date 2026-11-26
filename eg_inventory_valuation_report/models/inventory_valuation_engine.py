# -*- coding: utf-8 -*-
"""Inventory valuation reporting engine.

Single source of truth for every export format (PDF, XLSX): both call
``_build_dataset`` with the same validated parameters and render the returned
dictionary without performing any further calculation.

Accounting principles
---------------------
* Company-level figures (scope ``company``) are read exclusively from
  ``stock.valuation.layer`` (SVL), which is exactly what Odoo's native
  "Valuation" report and ``product.value_svl`` use.  Every layer up to the
  report end lands in exactly one bucket (opening, incoming, outgoing or
  adjustment), so ``opening + in - out + adj == closing`` holds by
  construction, for quantities and values.
* Warehouse / location views (scope ``warehouse`` / ``location``) cannot be
  derived from SVL because Odoo values stock per company, not per location.
  Quantities come from done ``stock.move.line`` records; values are an
  *allocation*: valued moves use their actual SVL unit cost, unvalued internal
  transfers and opening/closing balances use the company average unit cost at
  that moment.  The residual is shown separately as "cost allocation effect".
  These sections are always flagged as estimated.
* No ``sudo()``.  Products, locations and warehouses are obtained through the
  ORM (record rules apply); the SQL is restricted to the validated companies
  and to those ids, and is fully parameterised.
"""
import bisect
from collections import defaultdict
from datetime import datetime, time, timedelta
from decimal import Decimal

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools import float_is_zero, float_round

# key: (direction, label, sort order).  direction in ('in', 'out', 'adj')
MOVEMENT_TYPES = {
    'purchase': ('in', 'Purchase receipts', 10),
    'customer_return': ('in', 'Customer returns', 11),
    'production': ('in', 'Manufacturing output', 12),
    'unbuild_in': ('in', 'Unbuild output (components)', 13),
    'inventory_gain': ('in', 'Inventory adjustments (gains)', 14),
    'transit_in': ('in', 'Transit / inter-warehouse receipts', 15),
    'interco_in': ('in', 'Inter-company receipts', 16),
    'transfer_in': ('in', 'Internal transfers in (allocated)', 17),
    'dropship_in': ('in', 'Dropship (in)', 18),
    'other_in': ('in', 'Other receipts', 19),
    'delivery': ('out', 'Customer deliveries', 30),
    'vendor_return': ('out', 'Vendor returns', 31),
    'consumption': ('out', 'Manufacturing consumption', 32),
    'unbuild_out': ('out', 'Unbuilt products', 33),
    'scrap': ('out', 'Scrap', 34),
    'inventory_loss': ('out', 'Inventory adjustments (losses)', 35),
    'transit_out': ('out', 'Transit / inter-warehouse issues', 36),
    'interco_out': ('out', 'Inter-company issues', 37),
    'transfer_out': ('out', 'Internal transfers out (allocated)', 38),
    'dropship_out': ('out', 'Dropship (out)', 39),
    'other_out': ('out', 'Other issues', 40),
    'landed_cost': ('adj', 'Landed costs', 50),
    'price_diff': ('adj', 'Vendor bill price differences', 51),
    'revaluation': ('adj', 'Revaluations & standard cost changes', 52),
    'correction': ('adj', 'Negative-stock & other valuation corrections', 53),
    'cost_method_change': ('adj', 'Costing method / category change', 54),
    'allocation': ('adj', 'Cost allocation effect (estimated)', 55),
}

NUM_KEYS = ('open_qty', 'open_value', 'in_qty', 'in_value', 'out_qty', 'out_value',
            'adj_qty', 'adj_value', 'close_qty', 'close_value')
QTY_KEYS = ('open_qty', 'in_qty', 'out_qty', 'adj_qty', 'close_qty')
VALUE_KEYS = ('open_value', 'in_value', 'out_value', 'adj_value', 'close_value')

CLASSIC_KEYS = ('begin_qty', 'begin_value', 'in_qty', 'in_value', 'out_qty', 'out_value',
                'int_qty', 'int_value', 'adj_qty', 'adj_value', 'end_qty', 'end_value')

COST_METHOD_LABELS = {'standard': 'Standard', 'average': 'AVCO', 'fifo': 'FIFO'}
VALUATION_LABELS = {'real_time': 'Automated', 'manual_periodic': 'Manual'}

D0 = Decimal(0)


def _dec(value):
    if value is None:
        return D0
    return value if isinstance(value, Decimal) else Decimal(str(value))


class InventoryValuationEngine(models.AbstractModel):
    _name = 'eg.inventory.valuation.engine'
    _description = 'Inventory Valuation Reporting Engine'

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------
    @api.model
    def _build_dataset(self, params):
        """Compute the full report dataset.

        :param dict params: validated parameters, see
            ``inventory.valuation.report._get_engine_params``
        :return: dict (see module documentation, doc/TECHNICAL.md)
        """
        self._check_engine_access()
        p = self._normalise_params(params)
        companies = p['companies']
        products = self._get_products(p)
        cat_info = self._get_category_info(products, companies)
        product_info = self._get_product_info(products)

        # Authoritative company-level valuation is always computed: it is the
        # report itself in company scope and the reconciliation reference in
        # allocated scopes.
        company_rows, company_breakdown = self._compute_company_valuation(p, products.ids)

        if p['scope'] == 'company':
            raw_rows, breakdown = company_rows, company_breakdown
            sections_def = [{'key': (c.id, None), 'company': c, 'label': _('Company valuation'),
                             'allocated': False} for c in companies]
        else:
            sections_def = self._get_allocated_sections(p)
            raw_rows, breakdown = self._compute_allocated_valuation(p, products, sections_def)

        rows_by_section = self._finalise_rows(p, raw_rows, product_info, cat_info, sections_def, products)
        sections = self._assemble_sections(p, sections_def, rows_by_section)

        dataset = {
            'meta': self._get_meta(p, products),
            'companies': [self._company_info(c) for c in companies],
            'sections': sections,
            'currency_totals': self._currency_totals(sections),
            'breakdown': self._finalise_breakdown(p, breakdown, product_info, sections_def, rows_by_section),
            'movement_types': [{'key': k, 'direction': v[0], 'label': v[1]}
                               for k, v in sorted(MOVEMENT_TYPES.items(), key=lambda kv: kv[1][2])],
        }
        dataset['reconciliation'] = self._build_reconciliation(p, product_info, company_rows, cat_info, sections)
        dataset['exceptions'] = self._build_exceptions(sections)
        self._physical_vs_valued(p, product_info, company_rows, cat_info, dataset)
        dataset['location_sheets'] = self._build_location_sheets(
            p, products, product_info, cat_info, dataset,
            rows_by_section if p['scope'] == 'location' else None,
            sections_def if p['scope'] == 'location' else None,
            breakdown if p['scope'] == 'location' else None)
        return dataset

    # ------------------------------------------------------------------
    # Location sheets (classic layout: Begin / In / Out / Internal / Adjust / End)
    # ------------------------------------------------------------------
    def _build_location_sheets(self, p, products, product_info, cat_info, dataset,
                               rows_by=None, sdefs=None, brk=None):
        """Per-location figures in the classic column layout, plus a compiled
        "All locations" view per company.

        Same allocation engine as the warehouse/location scope.  Columns:
        In / Out = movements with the outside world (suppliers, customers,
        production, other companies); Internal = net transfers with other
        stock locations of the company; Adjust = inventory counts and scrap
        (quantity) plus value-only effects (landed costs, revaluations,
        cost allocation); End = Begin + In - Out + Internal + Adjust.
        """
        if not p.get('location_sheets'):
            return None
        if rows_by is None:
            p2 = {k: v for k, v in p.items() if k != 'loc_to_section'}
            p2['scope'] = 'location'
            sdefs = self._get_allocated_sections(p2)
            raw, brk = self._compute_allocated_valuation(p2, products, sdefs)
            rows_by = self._finalise_rows(p2, raw, product_info, cat_info, sdefs, products)
        digits = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        rq = lambda v: float_round(float(v), precision_digits=digits)  # noqa: E731
        books = {r['company_name']: r['authoritative_close_value'] for r in dataset['reconciliation']}
        sheets, by_company = [], defaultdict(list)
        for sdef in sdefs:
            rows = rows_by.get(sdef['key'], [])
            if not rows:
                continue
            cur = sdef['company'].currency_id
            lines = []
            for r in rows:
                t = brk.get((sdef['key'][0], sdef['key'][1], r['product_id']), {})

                def qv(*types):
                    return (sum((t[x][0] for x in types if x in t), D0),
                            sum((t[x][1] for x in types if x in t), D0))
                tin_q, tin_v = qv('transfer_in')
                tout_q, tout_v = qv('transfer_out')                 # negative
                gain_q, gain_v = qv('inventory_gain')
                loss_q, loss_v = qv('inventory_loss', 'scrap')      # negative
                line = {
                    'product_id': r['product_id'], 'code': r['code'], 'categ_name': r['categ_name'],
                    'name': ('[%s] %s' % (r['code'], r['name'])) if r['code'] else r['name'],
                    'cost_method': r['cost_method'], 'cost_method_key': r.get('cost_method_key', ''),
                    'uom': r['uom'], 'uom_id': r['uom_id'],
                    'flags': r['flags'],
                    'begin_qty': r['open_qty'], 'begin_value': r['open_value'],
                    'in_qty': rq(r['in_qty'] - float(tin_q + gain_q)),
                    'in_value': cur.round(r['in_value'] - float(tin_v + gain_v)),
                    'out_qty': rq(r['out_qty'] + float(tout_q + loss_q)),
                    'out_value': cur.round(r['out_value'] + float(tout_v + loss_v)),
                    'int_qty': rq(tin_q + tout_q), 'int_value': cur.round(float(tin_v + tout_v)),
                    'adj_qty': rq(gain_q + loss_q),
                    'end_qty': r['close_qty'], 'end_value': r['close_value'],
                }
                # value adjustment = everything else, so the row always reconciles
                line['adj_value'] = cur.round(line['end_value'] - line['begin_value'] - line['in_value']
                                              + line['out_value'] - line['int_value'])
                lines.append(line)
            sheet = {
                'company_id': sdef['company'].id, 'company_name': sdef['company'].name,
                'currency': self._currency_info(cur),
                'location_id': sdef.get('location_id'), 'location_name': sdef.get('location_name') or sdef['label'],
                'groups': self._classic_groups(p, lines, cur), 'totals': self._classic_totals(lines, cur),
            }
            sheets.append(sheet)
            by_company[sdef['company'].id].append(sheet)
        compiled = []
        for company in p['companies']:
            csheets = by_company.get(company.id)
            if not csheets:
                continue
            cur = company.currency_id
            merged = {}
            for sh in csheets:
                for g in sh['groups']:
                    for ln in g['lines']:
                        m = merged.setdefault(ln['product_id'], dict(ln, flags=[], **{k: 0.0 for k in CLASSIC_KEYS}))
                        for k in CLASSIC_KEYS:
                            m[k] += ln[k]
            lines = []
            for m in merged.values():
                for k in CLASSIC_KEYS:
                    m[k] = cur.round(m[k]) if k.endswith('_value') else rq(m[k])
                lines.append(m)
            lines.sort(key=lambda x: (x['categ_name'].lower(), x['code'].lower(), x['name'].lower()))
            totals = self._classic_totals(lines, cur)
            book = books.get(company.name)
            compiled.append({
                'company_id': company.id, 'company_name': company.name, 'currency': self._currency_info(cur),
                'groups': self._classic_groups(p, lines, cur), 'totals': totals,
                'by_location': [{'location_name': sh['location_name'], 'totals': sh['totals']} for sh in csheets],
                'books_close_value': book,
                'difference': cur.round(totals['end_value'] - book) if book is not None else None,
                'all_locations': not p.get('location_ids'),
            })
        return {'sheets': sheets, 'compiled': compiled}

    def _classic_groups(self, p, lines, cur):
        lines = sorted(lines, key=lambda x: (x['categ_name'].lower(), x['code'].lower(), x['name'].lower()))
        if p['group_by'] != 'category':
            return [{'label': '', 'lines': lines, 'totals': self._classic_totals(lines, cur)}]
        groups = defaultdict(list)
        for ln in lines:
            groups[ln['categ_name']].append(ln)
        return [{'label': name or _('Undefined category'), 'lines': g, 'totals': self._classic_totals(g, cur)}
                for name, g in sorted(groups.items(), key=lambda kv: kv[0].lower())]

    def _classic_totals(self, lines, cur):
        digits = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        uniform = len({ln['uom_id'] for ln in lines}) <= 1
        tot = {}
        for k in CLASSIC_KEYS:
            s = sum(ln[k] for ln in lines)
            if k.endswith('_value'):
                tot[k] = cur.round(s)
            else:
                tot[k] = float_round(s, precision_digits=digits) if uniform else None
        tot['uom'] = lines[0]['uom'] if (uniform and lines) else ''
        tot['count'] = len(lines)
        return tot

    def _physical_vs_valued(self, p, product_info, company_rows, cat_info, dataset):
        """Control: physical quantity (done stock moves in valued locations,
        consignment excluded) vs valued quantity (valuation layers), per product,
        at the end date.  Catches stock that exists physically but was never
        valued (e.g. counted before stock_account was installed, imported quants)
        or valuation layers without matching stock.  Differences are reported as
        exceptions; nothing is adjusted."""
        digits = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        rec_by_company = {r['company_name']: r for r in dataset['reconciliation']}
        for company in p['companies']:
            rec = rec_by_company[company.name]
            if p['date_basis'] != 'valuation':
                rec['qty_check'] = {'ok': None, 'count': 0, 'note': _(
                    "Not applicable with the journal entry date basis.")}
                continue
            locs = self.env['stock.location'].with_context(
                active_test=False, allowed_company_ids=p['companies'].ids).search([
                    ('company_id', '=', company.id), '|', ('usage', '=', 'internal'), ('usage', '=', 'transit')]
                + self._unvalued_location_domain())
            physical = defaultdict(lambda: D0)
            if locs and product_info:
                self.env.cr.execute("""
                    SELECT product_id, SUM(qty) FROM (
                        SELECT ml.product_id, ml.quantity_product_uom AS qty
                          FROM stock_move_line ml JOIN res_company rc ON rc.id = ml.company_id
                         WHERE ml.state = 'done' AND ml.product_id = ANY(%(products)s)
                           AND ml.location_dest_id = ANY(%(locs)s) AND NOT (ml.location_id = ANY(%(locs)s))
                           AND ml.date < %(end)s AND (ml.owner_id IS NULL OR ml.owner_id = rc.partner_id)
                        UNION ALL
                        SELECT ml.product_id, -ml.quantity_product_uom
                          FROM stock_move_line ml JOIN res_company rc ON rc.id = ml.company_id
                         WHERE ml.state = 'done' AND ml.product_id = ANY(%(products)s)
                           AND ml.location_id = ANY(%(locs)s) AND NOT (ml.location_dest_id = ANY(%(locs)s))
                           AND ml.date < %(end)s AND (ml.owner_id IS NULL OR ml.owner_id = rc.partner_id)
                    ) x GROUP BY product_id
                """, {'products': list(product_info), 'locs': locs.ids, 'end': p['end_utc']})
                for product_id, qty in self.env.cr.fetchall():
                    physical[product_id] = _dec(qty)
            items = []
            for pid in set(physical) | {k[2] for k in company_rows if k[0] == company.id}:
                info = product_info.get(pid)
                if not info or not info['is_storable'] and not physical.get(pid):
                    continue
                ci = cat_info.get((company.id, info['categ_id']), {})
                if p['cost_method'] != 'all' and ci.get('cost_method') != p['cost_method']:
                    continue
                if p['valuation_type'] != 'all' and ci.get('valuation') != p['valuation_type']:
                    continue
                phys = float_round(float(physical.get(pid, D0)), precision_digits=digits)
                valued = float_round(float(company_rows.get((company.id, None, pid), {}).get('close_qty', D0)),
                                     precision_digits=digits)
                if float_is_zero(phys - valued, precision_digits=digits):
                    continue
                items.append({'company_name': company.name, 'section': _('Company valuation'),
                              'code': info['code'], 'name': info['name'], 'uom': info['uom'],
                              'physical_qty': phys, 'valued_qty': valued,
                              'close_qty': phys, 'close_value': float(company_rows.get(
                                  (company.id, None, pid), {}).get('close_value', D0)),
                              'currency': company.currency_id.name,
                              'issue': _('Physical stock %(phys)s %(uom)s vs valued quantity %(val)s: '
                                         'stock not (fully) valued', phys=phys, uom=info['uom'], val=valued)})
            items.sort(key=lambda i: (i['code'], i['name']))
            rec['qty_check'] = {
                'ok': not items, 'count': len(items),
                'note': _("Physical quantity from done stock moves (company locations, consignment excluded) "
                          "compared with the quantity in valuation layers at %s.", p['date_to'])
                if not items else _("%s product(s) hold physical stock that differs from the valued quantity. "
                                    "Typical causes: stock counted before inventory valuation was enabled, "
                                    "imported quants, or data corrections made outside Odoo.", len(items)),
            }
            dataset['exceptions'].extend(items)

    # ------------------------------------------------------------------
    # Parameters & security
    # ------------------------------------------------------------------
    def _check_engine_access(self):
        # Native valuation layers are restricted to inventory administrators;
        # never widen that with sudo().
        if not self.env['stock.valuation.layer'].has_access('read'):
            raise AccessError(_("You are not allowed to read inventory valuation data. "
                                "Ask an Inventory Administrator for access."))

    def _normalise_params(self, params):
        p = dict(params)
        companies = self.env['res.company'].browse(p['company_ids']).exists()
        if not companies:
            raise UserError(_("Select at least one company."))
        allowed = self.env.user.company_ids
        if companies - allowed:
            raise AccessError(_("You are not allowed to report on: %s",
                                ", ".join((companies - allowed).mapped('name'))))
        p['companies'] = companies.sorted(lambda c: (c.sequence, c.name))
        tz_name = p.get('tz') or 'UTC'
        try:
            tz = pytz.timezone(tz_name)
        except pytz.UnknownTimeZoneError:
            tz, tz_name = pytz.utc, 'UTC'
        p['tz'], p['tz_obj'] = tz_name, tz
        date_to = fields.Date.to_date(p['date_to'])
        date_from = fields.Date.to_date(p.get('date_from')) if p.get('report_type') == 'period' else None
        if date_from and date_from > date_to:
            raise UserError(_("The start date must be on or before the end date."))
        p['date_to'], p['date_from'] = date_to, date_from

        def to_utc(d):
            return tz.localize(datetime.combine(d, time.min)).astimezone(pytz.utc).replace(tzinfo=None)

        p['end_utc'] = to_utc(date_to + timedelta(days=1))          # exclusive
        p['start_utc'] = to_utc(date_from) if date_from else p['end_utc']
        # In "as of" mode the opening boundary is the end boundary: every
        # layer is part of the (closing) balance and no movement is listed.
        p['eff_date_from'] = date_from or (date_to + timedelta(days=1))
        if p.get('date_basis') not in ('valuation', 'accounting'):
            p['date_basis'] = 'valuation'
        if p['scope'] not in ('company', 'warehouse', 'location'):
            raise UserError(_("Invalid report scope."))
        if p['scope'] != 'company':
            # Physical quantities per location only exist at stock move dates.
            p['date_basis'] = 'valuation'
        p.setdefault('stock_filter', 'active')
        p.setdefault('cost_method', 'all')
        p.setdefault('valuation_type', 'all')
        p.setdefault('group_by', 'category')
        p.setdefault('detail_level', 'detailed')
        return p

    def _get_products(self, p):
        Product = self.env['product.product'].with_context(
            active_test=not p.get('include_archived', True),
            allowed_company_ids=p['companies'].ids)
        domain = [('type', '=', 'consu'),
                  ('company_id', 'in', p['companies'].ids + [False])]
        if p.get('product_ids'):
            domain.append(('id', 'in', p['product_ids']))
        if p.get('category_ids'):
            domain.append(('categ_id', 'child_of', p['category_ids']))
        return Product.search(domain, order='id')

    def _get_category_info(self, products, companies):
        """(company_id, categ_id) -> costing method / valuation / account (company-dependent)."""
        info = {}
        categs = products.with_context(active_test=False).categ_id
        has_acc = 'property_stock_valuation_account_id' in self.env['product.category']._fields
        for company in companies:
            for categ in categs.with_company(company):
                acc = categ.property_stock_valuation_account_id if has_acc else False
                info[(company.id, categ.id)] = {
                    'cost_method': categ.property_cost_method,
                    'valuation': categ.property_valuation,
                    'account_id': acc.id if acc else False,
                    'account_name': acc.display_name if acc else '',
                }
        return info

    def _get_product_info(self, products):
        info = {}
        prods = products.with_context(active_test=False, display_default_code=False)
        prec = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for prod in prods:
            info[prod.id] = {
                'id': prod.id,
                'code': prod.default_code or '',
                'name': prod.display_name,
                'categ_id': prod.categ_id.id,
                'categ_name': prod.categ_id.complete_name or '',
                'uom_id': prod.uom_id.id,
                'uom': prod.uom_id.name,
                'uom_rounding': prod.uom_id.rounding or 10 ** -prec,
                'active': prod.active,
                'is_storable': prod.is_storable,
                'standard_price': prod.standard_price,
            }
        return info

    # ------------------------------------------------------------------
    # Company-level (authoritative) valuation
    # ------------------------------------------------------------------
    def _optional_sql(self):
        """SQL fragments depending on installed modules (static strings only)."""
        Move = self.env['stock.move']
        SVL = self.env['stock.valuation.layer']
        has_unbuild = 'unbuild_id' in Move._fields and Move._fields['unbuild_id'].store
        has_consume_unbuild = 'consume_unbuild_id' in Move._fields and Move._fields['consume_unbuild_id'].store
        has_landed = 'stock_landed_cost_id' in SVL._fields and SVL._fields['stock_landed_cost_id'].store
        never = "WHEN FALSE THEN NULL"
        return {
            'unbuild_in': "WHEN sm.unbuild_id IS NOT NULL THEN 'unbuild_in'" if has_unbuild else never,
            # Odoo 18 links every unbuild move through unbuild_id (consumed finished
            # product and returned components alike); consume_unbuild_id is kept for safety.
            'unbuild_out': ("WHEN sm.unbuild_id IS NOT NULL%s THEN 'unbuild_out'" % (
                " OR sm.consume_unbuild_id IS NOT NULL" if has_consume_unbuild else "")) if has_unbuild else never,
            'landed': "svl.stock_landed_cost_id IS NOT NULL" if has_landed else "FALSE",
        }

    def _bucket_case_sql(self, opt):
        return """
            CASE
              WHEN svl.quantity = 0 THEN
                CASE WHEN {landed} THEN 'landed_cost'
                     WHEN svl.account_move_line_id IS NOT NULL THEN 'price_diff'
                     WHEN svl.stock_move_id IS NULL THEN 'revaluation'
                     ELSE 'correction' END
              WHEN svl.stock_move_id IS NULL THEN 'cost_method_change'
              WHEN svl.quantity > 0 THEN
                CASE WHEN sl.usage = 'supplier' AND dl.usage = 'customer' THEN 'dropship_in'
                     WHEN sl.usage = 'supplier' THEN 'purchase'
                     WHEN sl.usage = 'customer' THEN 'customer_return'
                     WHEN sl.usage = 'inventory' THEN 'inventory_gain'
                     WHEN sl.usage = 'production' THEN
                        CASE {unbuild_in} ELSE 'production' END
                     WHEN sl.usage = 'transit' THEN 'transit_in'
                     WHEN sl.usage = 'internal' THEN 'interco_in'
                     ELSE 'other_in' END
              ELSE
                CASE WHEN sl.usage = 'supplier' AND dl.usage = 'customer' THEN 'dropship_out'
                     WHEN dl.usage = 'customer' THEN 'delivery'
                     WHEN dl.usage = 'supplier' THEN 'vendor_return'
                     WHEN dl.scrap_location OR sm.scrap_id IS NOT NULL THEN 'scrap'
                     WHEN dl.usage = 'inventory' THEN 'inventory_loss'
                     WHEN dl.usage = 'production' THEN
                        CASE {unbuild_out} ELSE 'consumption' END
                     WHEN dl.usage = 'transit' THEN 'transit_out'
                     WHEN dl.usage = 'internal' THEN 'interco_out'
                     ELSE 'other_out' END
            END""".format(**opt)

    def _compute_company_valuation(self, p, product_ids):
        """Aggregate valuation layers per (company, product, bucket).

        :return: (rows, breakdown) where rows maps (company_id, None, product_id)
                 to a dict of Decimal figures and breakdown maps the same key to
                 {movement_type: [qty, value]}.
        """
        rows, breakdown = {}, defaultdict(lambda: defaultdict(lambda: [D0, D0]))
        if not product_ids:
            return rows, breakdown
        opt = self._optional_sql()
        bucket_case = self._bucket_case_sql(opt)
        if p['date_basis'] == 'accounting':
            # Journal entry date when the layer has an accounting entry
            # (automated valuation); otherwise the layer's local date.
            eff = ("COALESCE(am.date, (svl.create_date AT TIME ZONE 'UTC' "
                   "AT TIME ZONE %(tz)s)::date)")
            am_join = "LEFT JOIN account_move am ON am.id = svl.account_move_id"
            is_open = eff + " < %(date_from)s"
            in_range = eff + " <= %(date_to)s"
        else:
            am_join = ""
            is_open = "svl.create_date < %(start_utc)s"
            in_range = "svl.create_date < %(end_utc)s"
        query = """
            SELECT svl.company_id, svl.product_id,
                   CASE WHEN {is_open} THEN 'opening' ELSE {bucket_case} END AS bucket,
                   SUM(svl.quantity), SUM(svl.value)
              FROM stock_valuation_layer svl
              LEFT JOIN stock_move sm ON sm.id = svl.stock_move_id
              LEFT JOIN stock_location sl ON sl.id = sm.location_id
              LEFT JOIN stock_location dl ON dl.id = sm.location_dest_id
              {am_join}
             WHERE svl.company_id = ANY(%(company_ids)s)
               AND svl.product_id = ANY(%(product_ids)s)
               AND {in_range}
          GROUP BY 1, 2, 3
        """.format(is_open=is_open, bucket_case=bucket_case, am_join=am_join, in_range=in_range)
        self.env['stock.valuation.layer'].flush_model()
        self.env['stock.move'].flush_model()
        self.env.cr.execute(query, {
            'company_ids': p['companies'].ids, 'product_ids': list(product_ids),
            'start_utc': p['start_utc'], 'end_utc': p['end_utc'], 'tz': p['tz'],
            'date_from': p['eff_date_from'], 'date_to': p['date_to'],
        })
        for company_id, product_id, bucket, qty, value in self.env.cr.fetchall():
            key = (company_id, None, product_id)
            row = rows.setdefault(key, dict.fromkeys(NUM_KEYS, D0))
            qty, value = _dec(qty), _dec(value)
            if bucket == 'opening':
                row['open_qty'] += qty
                row['open_value'] += value
            else:
                direction = MOVEMENT_TYPES[bucket][0]
                if direction == 'in':
                    row['in_qty'] += qty
                    row['in_value'] += value
                elif direction == 'out':
                    row['out_qty'] -= qty
                    row['out_value'] -= value
                else:
                    row['adj_qty'] += qty
                    row['adj_value'] += value
                breakdown[key][bucket][0] += qty
                breakdown[key][bucket][1] += value
            row['close_qty'] += qty
            row['close_value'] += value
        return rows, breakdown

    # ------------------------------------------------------------------
    # Allocated (warehouse / location) valuation
    # ------------------------------------------------------------------
    def _get_allocated_sections(self, p):
        """Return section definitions and attach a location -> section map to p."""
        Location = self.env['stock.location'].with_context(allowed_company_ids=p['companies'].ids)
        companies = p['companies']
        loc_to_section = {}
        sections = []
        if p['scope'] == 'warehouse':
            warehouses = self.env['stock.warehouse'].with_context(
                allowed_company_ids=companies.ids, active_test=False).search(
                [('company_id', 'in', companies.ids)] + (
                    [('id', 'in', p['warehouse_ids'])] if p.get('warehouse_ids') else []),
                order='company_id, sequence, id')
            for wh in warehouses:
                sections.append({'key': (wh.company_id.id, wh.id), 'company': wh.company_id,
                                 'label': _('Warehouse: %s', wh.display_name), 'allocated': True,
                                 'warehouse_id': wh.id})
            # Valued locations: internal + company transit (Odoo's _should_be_valued)
            valued = Location.with_context(active_test=False).search([
                ('company_id', 'in', companies.ids),
                '|', ('usage', '=', 'internal'), ('usage', '=', 'transit')] + self._unvalued_location_domain())
            wh_ids = set(warehouses.ids)
            for loc in valued:
                if loc.warehouse_id.id in wh_ids:
                    loc_to_section[loc.id] = (loc.company_id.id, loc.warehouse_id.id)
                elif not p.get('warehouse_ids'):
                    loc_to_section[loc.id] = (loc.company_id.id, 0)
            if not p.get('warehouse_ids'):
                for company in companies:
                    if any(v == (company.id, 0) for v in loc_to_section.values()):
                        sections.append({'key': (company.id, 0), 'company': company,
                                         'label': _('Locations outside warehouses (transit, etc.)'),
                                         'allocated': True, 'warehouse_id': False})
        else:
            # One section per location.  Selected locations (or, when none is
            # selected, every top-level stock location) each include their
            # sub-locations; a location is counted in exactly one section (its
            # nearest selected ancestor), so nothing is counted twice.
            valued_domain = [('company_id', 'in', companies.ids),
                             '|', ('usage', '=', 'internal'), ('usage', '=', 'transit')] \
                + self._unvalued_location_domain()
            AllLoc = Location.with_context(active_test=False)
            if p.get('location_ids'):
                selected = AllLoc.search([('id', 'in', p['location_ids']), ('company_id', 'in', companies.ids)])
                if not selected:
                    raise UserError(_("None of the selected locations belongs to the selected companies."))
                candidates = AllLoc.search([('id', 'child_of', selected.ids)] + valued_domain)
                roots = set(selected.ids)
                deepest = True
            else:
                candidates = AllLoc.search(valued_domain)
                roots = set(candidates.ids)
                deepest = False
            for loc in candidates:
                path = [int(x) for x in (loc.parent_path or '').split('/') if x]
                if deepest:
                    root = next((i for i in reversed(path) if i in roots), None)
                else:
                    root = next((i for i in path if i in roots), None)
                if root:
                    loc_to_section[loc.id] = (loc.company_id.id, root)
            for root in AllLoc.browse(sorted({r for _c, r in loc_to_section.values()})):
                sections.append({'key': (root.company_id.id, root.id), 'company': root.company_id,
                                 'label': _('Location: %s', root.complete_name), 'allocated': True,
                                 'warehouse_id': False, 'location_id': root.id,
                                 'location_name': root.complete_name})
        p['loc_to_section'] = loc_to_section
        # sort: by company order then label
        order = {c.id: i for i, c in enumerate(companies)}
        sections.sort(key=lambda s: (order[s['key'][0]], s['key'][1] in (0, -1), s['label'].lower()))
        return sections

    def _unvalued_location_domain(self):
        """Locations Odoo never values although they are 'internal' (mirror of
        stock.location._should_be_valued overrides), e.g. subcontractor locations."""
        if 'is_subcontracting_location' in self.env['stock.location']._fields:
            return [('is_subcontracting_location', '=', False)]
        return []

    def _company_avg_cost(self, p, product_ids, utc_bound):
        """Company average unit cost per (company, product) for layers created before utc_bound.

        Falls back to the unit cost of the latest quantity-bearing layer when
        the company quantity is zero or negative.
        """
        res = {}
        if not product_ids:
            return res
        self.env.cr.execute("""
            SELECT company_id, product_id, SUM(quantity), SUM(value)
              FROM stock_valuation_layer
             WHERE company_id = ANY(%s) AND product_id = ANY(%s) AND create_date < %s
          GROUP BY 1, 2
        """, (p['companies'].ids, list(product_ids), utc_bound))
        for company_id, product_id, qty, value in self.env.cr.fetchall():
            qty, value = _dec(qty), _dec(value)
            if qty > 0:
                res[(company_id, product_id)] = value / qty
        self.env.cr.execute("""
            SELECT DISTINCT ON (company_id, product_id) company_id, product_id, unit_cost
              FROM stock_valuation_layer
             WHERE company_id = ANY(%s) AND product_id = ANY(%s) AND create_date < %s AND quantity <> 0
          ORDER BY company_id, product_id, create_date DESC, id DESC
        """, (p['companies'].ids, list(product_ids), utc_bound))
        for company_id, product_id, unit_cost in self.env.cr.fetchall():
            res.setdefault((company_id, product_id), _dec(unit_cost))
        return res

    def _avg_cost_series(self, p, pairs):
        """Cumulative (timestamp, avg unit cost) series for the given (company, product) pairs."""
        series = defaultdict(lambda: ([], []))
        if not pairs:
            return series
        companies = sorted({c for c, _p in pairs})
        prods = sorted({pr for _c, pr in pairs})
        self.env.cr.execute("""
            SELECT company_id, product_id, create_date, quantity, value, unit_cost
              FROM stock_valuation_layer
             WHERE company_id = ANY(%s) AND product_id = ANY(%s) AND create_date < %s
          ORDER BY company_id, product_id, create_date, id
        """, (companies, prods, p['end_utc']))
        cum = {}
        for company_id, product_id, create_date, qty, value, unit_cost in self.env.cr.fetchall():
            key = (company_id, product_id)
            if key not in pairs:
                continue
            cq, cv, last = cum.get(key, (D0, D0, None))
            cq += _dec(qty)
            cv += _dec(value)
            if qty:
                last = _dec(unit_cost)
            cum[key] = (cq, cv, last)
            avg = cv / cq if cq > 0 else last
            stamps, values = series[key]
            stamps.append(create_date)
            values.append(avg)
        return series

    @staticmethod
    def _series_lookup(series, key, when, default):
        stamps, values = series.get(key, ([], []))
        i = bisect.bisect_right(stamps, when)
        if i and values[i - 1] is not None:
            return values[i - 1]
        return default

    def _compute_allocated_valuation(self, p, products, sections_def):
        rows = {}
        breakdown = defaultdict(lambda: defaultdict(lambda: [D0, D0]))
        loc_map = p['loc_to_section']
        if not loc_map or not products:
            return rows, breakdown
        product_ids = products.ids
        loc_ids = list(loc_map)
        self.env['stock.move.line'].flush_model()
        self.env['stock.move'].flush_model()
        # Consigned stock (owner other than the company) is not company stock.
        owner_clause = "(ml.owner_id IS NULL OR ml.owner_id = rc.partner_id)"

        # 1) opening / closing quantities per (product, location)
        self.env.cr.execute("""
            WITH lines AS (
                SELECT ml.product_id, ml.location_dest_id AS loc, ml.quantity_product_uom AS qty, ml.date
                  FROM stock_move_line ml JOIN res_company rc ON rc.id = ml.company_id
                 WHERE ml.state = 'done' AND ml.product_id = ANY(%(products)s)
                   AND ml.location_dest_id = ANY(%(locs)s) AND ml.date < %(end)s AND {owner}
                UNION ALL
                SELECT ml.product_id, ml.location_id, -ml.quantity_product_uom, ml.date
                  FROM stock_move_line ml JOIN res_company rc ON rc.id = ml.company_id
                 WHERE ml.state = 'done' AND ml.product_id = ANY(%(products)s)
                   AND ml.location_id = ANY(%(locs)s) AND ml.date < %(end)s AND {owner}
            )
            SELECT product_id, loc,
                   COALESCE(SUM(qty) FILTER (WHERE date < %(start)s), 0), SUM(qty)
              FROM lines GROUP BY 1, 2
        """.format(owner=owner_clause), {'products': product_ids, 'locs': loc_ids,
                                          'start': p['start_utc'], 'end': p['end_utc']})
        balances = defaultdict(lambda: [D0, D0])
        for product_id, loc, open_q, close_q in self.env.cr.fetchall():
            sec = loc_map[loc]
            balances[(sec, product_id)][0] += _dec(open_q)
            balances[(sec, product_id)][1] += _dec(close_q)

        # 2) period movements crossing a section boundary
        opt = self._optional_sql()
        self.env.cr.execute("""
            SELECT ml.product_id, ml.location_id, ml.location_dest_id, ml.quantity_product_uom, ml.date,
                   sl.usage, dl.usage, (dl.scrap_location OR sm.scrap_id IS NOT NULL),
                   CASE {unbuild_in} ELSE NULL END, CASE {unbuild_out} ELSE NULL END,
                   mv.qty, mv.value, sl.company_id, dl.company_id
              FROM stock_move_line ml
              JOIN res_company rc ON rc.id = ml.company_id
              JOIN stock_move sm ON sm.id = ml.move_id
              JOIN stock_location sl ON sl.id = ml.location_id
              JOIN stock_location dl ON dl.id = ml.location_dest_id
              LEFT JOIN LATERAL (
                    SELECT SUM(s.quantity) AS qty, SUM(s.value) AS value
                      FROM stock_valuation_layer s
                     WHERE s.stock_move_id = sm.id AND s.quantity <> 0
              ) mv ON TRUE
             WHERE ml.state = 'done' AND ml.product_id = ANY(%(products)s)
               AND (ml.location_id = ANY(%(locs)s) OR ml.location_dest_id = ANY(%(locs)s))
               AND ml.date >= %(start)s AND ml.date < %(end)s AND {owner}
          ORDER BY ml.date, ml.id
        """.format(owner=owner_clause, unbuild_in=opt['unbuild_in'], unbuild_out=opt['unbuild_out']),
            {'products': product_ids, 'locs': loc_ids, 'start': p['start_utc'], 'end': p['end_utc']})
        lines = self.env.cr.fetchall()

        # unit costs
        open_cost = self._company_avg_cost(p, product_ids, p['start_utc'])
        close_cost = self._company_avg_cost(p, product_ids, p['end_utc'])
        unvalued_pairs = set()
        for line in lines:
            if not line[10]:
                sec = loc_map.get(line[1]) or loc_map.get(line[2])
                unvalued_pairs.add((sec[0], line[0]))
        series = self._avg_cost_series(p, unvalued_pairs)
        std_price = {pr.id: _dec(pr.standard_price) for pr in products}

        for (product_id, src, dst, qty, date, su, du, scrap, ub_in, ub_out, mv_q, mv_v, s_comp, d_comp) in lines:
            s_sec, d_sec = loc_map.get(src), loc_map.get(dst)
            if s_sec == d_sec:
                continue  # movement inside one section
            qty = _dec(qty)
            if mv_q:
                # valued move: actual unit cost of its valuation layers
                unit = abs(_dec(mv_v) / _dec(mv_q))
            else:
                # unvalued (internal) move: company average cost at that moment
                comp = (s_sec or d_sec)[0]
                unit = self._series_lookup(series, (comp, product_id), date,
                                           open_cost.get((comp, product_id), std_price[product_id]))
            value = qty * unit
            if d_sec:
                if s_sec:
                    mtype = 'transfer_in' if s_sec[0] == d_sec[0] else 'interco_in'
                elif su == 'internal':
                    mtype = 'transfer_in' if s_comp == d_sec[0] else 'interco_in'
                else:
                    mtype = self._ml_in_type(su, du, ub_in)
                key = (d_sec[0], d_sec[1], product_id)
                row = rows.setdefault(key, dict.fromkeys(NUM_KEYS, D0))
                row['in_qty'] += qty
                row['in_value'] += value
                if s_sec and s_sec[0] == d_sec[0]:
                    # transfer between two reported sections of one company:
                    # eliminated in consolidated totals
                    row['xfer_in_value'] = row.get('xfer_in_value', D0) + value
                breakdown[key][mtype][0] += qty
                breakdown[key][mtype][1] += value
            if s_sec:
                if d_sec:
                    mtype = 'transfer_out' if s_sec[0] == d_sec[0] else 'interco_out'
                elif du == 'internal':
                    mtype = 'transfer_out' if d_comp == s_sec[0] else 'interco_out'
                else:
                    mtype = self._ml_out_type(su, du, scrap, ub_out)
                key = (s_sec[0], s_sec[1], product_id)
                row = rows.setdefault(key, dict.fromkeys(NUM_KEYS, D0))
                row['out_qty'] += qty
                row['out_value'] += value
                if d_sec and s_sec[0] == d_sec[0]:
                    row['xfer_out_value'] = row.get('xfer_out_value', D0) + value
                breakdown[key][mtype][0] -= qty
                breakdown[key][mtype][1] -= value

        for (sec, product_id), (open_q, close_q) in balances.items():
            key = (sec[0], sec[1], product_id)
            row = rows.setdefault(key, dict.fromkeys(NUM_KEYS, D0))
            row['open_qty'] = open_q
            row['close_qty'] = close_q
        for key, row in rows.items():
            company_id, _sec, product_id = key
            oc = open_cost.get((company_id, product_id), std_price.get(product_id, D0))
            cc = close_cost.get((company_id, product_id), std_price.get(product_id, D0))
            row['open_value'] = row['open_qty'] * oc
            row['close_value'] = row['close_qty'] * cc
            row['_allocated'] = True
        return rows, breakdown

    @staticmethod
    def _ml_in_type(su, du, unbuild_in):
        if su == 'supplier':
            return 'purchase'
        if su == 'customer':
            return 'customer_return'
        if su == 'inventory':
            return 'inventory_gain'
        if su == 'production':
            return 'unbuild_in' if unbuild_in else 'production'
        if su == 'transit':
            return 'transit_in'
        return 'other_in'

    @staticmethod
    def _ml_out_type(su, du, scrap, unbuild_out):
        if du == 'customer':
            return 'delivery'
        if du == 'supplier':
            return 'vendor_return'
        if scrap:
            return 'scrap'
        if du == 'inventory':
            return 'inventory_loss'
        if du == 'production':
            return 'unbuild_out' if unbuild_out else 'consumption'
        if du == 'transit':
            return 'transit_out'
        return 'other_out'

    # ------------------------------------------------------------------
    # Rounding, filtering, grouping
    # ------------------------------------------------------------------
    def _finalise_rows(self, p, raw_rows, product_info, cat_info, sections_def, products):
        """Round figures, attach product data, apply filters.

        Rounding policy: values are rounded to the company currency, quantities
        to the product UoM rounding.  For allocated rows the adjustment column
        absorbs the rounding/allocation residual so that every row reconciles
        exactly.  For authoritative rows every column is an exact sum of
        already-rounded layer values, so rounding never changes the identity.
        """
        currency = {c.id: c.currency_id for c in p['companies']}
        section_keys = {s['key'] for s in sections_def}
        result = defaultdict(list)
        price_digits = self.env['decimal.precision'].precision_get('Product Price')
        qty_digits = self.env['decimal.precision'].precision_get('Product Unit of Measure')

        # include products without any activity when requested
        if p['stock_filter'] == 'all':
            storable = [pid for pid, info in product_info.items() if info['is_storable']]
            for sec in section_keys:
                for pid in storable:
                    raw_rows.setdefault((sec[0], sec[1], pid), dict.fromkeys(NUM_KEYS, D0))

        for (company_id, sec_id, product_id), raw in raw_rows.items():
            if (company_id, sec_id) not in section_keys:
                continue
            info = product_info.get(product_id)
            if not info:
                continue
            cinfo = cat_info.get((company_id, info['categ_id']), {})
            if p['cost_method'] != 'all' and cinfo.get('cost_method') != p['cost_method']:
                continue
            if p['valuation_type'] != 'all' and cinfo.get('valuation') != p['valuation_type']:
                continue
            cur = currency[company_id]
            rnd = 10 ** -qty_digits
            row = {}
            # Quantities are stored with the 'Product Unit of Measure' precision,
            # so rounding their exact (Decimal) sums to that precision is lossless.
            for k in QTY_KEYS:
                row[k] = float_round(float(raw[k]), precision_digits=qty_digits)
            for k in VALUE_KEYS:
                row[k] = cur.round(float(raw[k]))
            row['xfer_in_value'] = cur.round(float(raw.get('xfer_in_value', D0)))
            row['xfer_out_value'] = cur.round(float(raw.get('xfer_out_value', D0)))
            if raw.get('_allocated'):
                # quantities from move lines: no quantity adjustment exists;
                # the value residual is the (estimated) cost allocation effect.
                row['adj_qty'] = 0.0
            # Closing value is rounded once (exactly like Odoo's value_svl).  If
            # source layers carry sub-currency decimals, the rounding residual
            # is absorbed in adjustments and flagged, so the row reconciles.
            residual = cur.round(row['close_value'] - row['open_value'] - row['in_value']
                                 + row['out_value'] - row['adj_value'])
            row['rounding_residual'] = 0.0
            if not cur.is_zero(residual):
                if not raw.get('_allocated'):
                    row['rounding_residual'] = residual
                row['adj_value'] = cur.round(row['adj_value'] + residual)
            if not any(row[k] for k in NUM_KEYS):
                if p['stock_filter'] != 'all':
                    continue
            if p['stock_filter'] == 'nonzero' and \
                    float_is_zero(row['close_qty'], precision_rounding=rnd) and cur.is_zero(row['close_value']):
                continue
            row['unit_cost'] = (float_round(row['close_value'] / row['close_qty'], precision_digits=price_digits)
                                if not float_is_zero(row['close_qty'], precision_rounding=rnd) else None)
            row.update({
                'product_id': product_id,
                'code': info['code'],
                'name': info['name'],
                'categ_id': info['categ_id'],
                'categ_name': info['categ_name'],
                'uom_id': info['uom_id'],
                'uom': info['uom'],
                'active': info['active'],
                'cost_method': COST_METHOD_LABELS.get(cinfo.get('cost_method'), cinfo.get('cost_method') or ''),
                'cost_method_key': cinfo.get('cost_method') or '',
                'valuation': VALUATION_LABELS.get(cinfo.get('valuation'), ''),
                'valuation_key': cinfo.get('valuation'),
                'account_id': cinfo.get('account_id'),
                'allocated': bool(raw.get('_allocated')),
            })
            row['flag_codes'] = self._row_flags(row, rnd, cur)
            labels = self._flag_labels()
            row['flags'] = [labels[c] for c in row['flag_codes']]
            if row['rounding_residual']:
                row['flag_codes'].append('rounding')
                row['flags'].append(_('Rounding residual of %s included in adjustments', row['rounding_residual']))
            result[(company_id, sec_id)].append(row)
        for rows in result.values():
            rows.sort(key=lambda r: (r['categ_name'].lower(), r['code'].lower(), r['name'].lower(), r['product_id']))
        return result

    def _flag_labels(self):
        return {
            'negative': _('Negative stock'),
            'value_no_qty': _('Value without quantity'),
            'qty_no_value': _('Quantity without value'),
            'opposite_signs': _('Quantity and value have opposite signs'),
            'archived': _('Archived product'),
        }

    @staticmethod
    def _row_flags(row, rnd, cur):
        """Audit flag codes for a row (labels are translated separately)."""
        flags = []
        zero_qty = float_is_zero(row['close_qty'], precision_rounding=rnd)
        if row['close_qty'] < 0 and not zero_qty:
            flags.append('negative')
        if zero_qty and not cur.is_zero(row['close_value']):
            flags.append('value_no_qty')
        if not zero_qty and row['close_qty'] > 0 and cur.is_zero(row['close_value']):
            flags.append('qty_no_value')
        if not zero_qty and (row['close_qty'] > 0) != (row['close_value'] > 0) and not cur.is_zero(row['close_value']):
            flags.append('opposite_signs')
        if not row['active']:
            flags.append('archived')
        return flags

    def _sum(self, rows, currency):
        tot = {k: 0.0 for k in NUM_KEYS}
        uoms = {r['uom_id'] for r in rows}
        for r in rows:
            for k in NUM_KEYS:
                tot[k] += r[k]
        for k in VALUE_KEYS:
            tot[k] = currency.round(tot[k])
        uniform = len(uoms) <= 1
        if uniform:
            digits = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            for k in QTY_KEYS:
                tot[k] = float_round(tot[k], precision_digits=digits)
        else:
            for k in QTY_KEYS:
                tot[k] = None  # never add quantities in different units
        tot['uom'] = rows[0]['uom'] if (uniform and rows) else ''
        tot['xfer_in_value'] = currency.round(sum(r.get('xfer_in_value', 0.0) for r in rows))
        tot['xfer_out_value'] = currency.round(sum(r.get('xfer_out_value', 0.0) for r in rows))
        tot['count'] = len(rows)
        tot['unit_cost'] = None
        return tot

    def _assemble_sections(self, p, sections_def, rows_by_section):
        sections = []
        for sdef in sections_def:
            company = sdef['company']
            rows = rows_by_section.get(sdef['key'], [])
            if sdef['allocated'] and not rows:
                continue  # empty warehouse / location section: nothing to show
            groups = []
            if p['group_by'] == 'category':
                by_cat = defaultdict(list)
                for r in rows:
                    by_cat[(r['categ_name'], r['categ_id'])].append(r)
                for (cname, cid), crow in sorted(by_cat.items(), key=lambda kv: kv[0][0].lower()):
                    groups.append({'label': cname or _('Undefined category'), 'categ_id': cid,
                                   'rows': crow, 'totals': self._sum(crow, company.currency_id)})
            else:
                groups.append({'label': '', 'categ_id': False, 'rows': rows,
                               'totals': self._sum(rows, company.currency_id)})
            sections.append({
                'key': '%s-%s' % sdef['key'],
                'company_id': company.id,
                'company_name': company.name,
                'currency': self._currency_info(company.currency_id),
                'label': sdef['label'],
                'allocated': sdef['allocated'],
                'groups': groups,
                'totals': self._sum(rows, company.currency_id),
                'product_count': len(rows),
            })
        return sections

    def _currency_totals(self, sections):
        """Consolidated totals per currency (never across currencies).

        Transfers between two reported warehouses/locations of the same
        company are eliminated from incoming and outgoing, so internal
        movements never inflate consolidated receipts or deliveries.  The same
        amount is removed from both sides, which keeps the identity exact.
        Inter-company flows are NOT eliminated (separate legal entities).
        """
        res = {}
        for sec in sections:
            cur = sec['currency']
            entry = res.setdefault((cur['id'], sec['allocated']), {
                'currency': cur, 'allocated': sec['allocated'], 'companies': [],
                'transfers_eliminated': 0.0, **{k: 0.0 for k in VALUE_KEYS}})
            for k in VALUE_KEYS:
                entry[k] += sec['totals'][k]
            entry['transfers_eliminated'] += sec['totals'].get('xfer_in_value', 0.0)
            if sec['company_name'] not in entry['companies']:
                entry['companies'].append(sec['company_name'])
        out = []
        for entry in res.values():
            currency = self.env['res.currency'].browse(entry['currency']['id'])
            elim = currency.round(entry['transfers_eliminated'])
            entry['in_value'] -= elim
            entry['out_value'] -= elim
            entry['transfers_eliminated'] = elim
            for k in VALUE_KEYS:
                entry[k] = currency.round(entry[k])
            out.append(entry)
        return out

    def _finalise_breakdown(self, p, breakdown, product_info, sections_def, rows_by_section):
        """Long-format movement analysis, restricted to rows kept in the report."""
        kept = {(sec_key, r['product_id']) for sec_key, rows in rows_by_section.items() for r in rows}
        sec_by_key = {s['key']: s for s in sections_def}
        out = []
        for (company_id, sec_id, product_id), types in breakdown.items():
            sec_key = (company_id, sec_id)
            if (sec_key, product_id) not in kept:
                continue
            sdef = sec_by_key[sec_key]
            cur = sdef['company'].currency_id
            info = product_info[product_id]
            for mtype, (qty, value) in types.items():
                direction, label, seq = MOVEMENT_TYPES[mtype]
                out.append({
                    'company_name': sdef['company'].name,
                    'section': sdef['label'],
                    'allocated': sdef['allocated'],
                    'currency': cur.name,
                    'code': info['code'], 'name': info['name'], 'categ_name': info['categ_name'],
                    'uom': info['uom'],
                    'type': mtype, 'type_label': label, 'direction': direction, 'seq': seq,
                    'qty': float_round(float(qty), precision_rounding=info['uom_rounding']),
                    'value': cur.round(float(value)),
                })
        # allocation residuals are part of the reconciliation too
        for sec_key, rows in rows_by_section.items():
            sdef = sec_by_key[sec_key]
            for r in rows:
                if r['allocated'] and r['adj_value']:
                    out.append({
                        'company_name': sdef['company'].name, 'section': sdef['label'], 'allocated': True,
                        'currency': sdef['company'].currency_id.name,
                        'code': r['code'], 'name': r['name'], 'categ_name': r['categ_name'], 'uom': r['uom'],
                        'type': 'allocation', 'type_label': MOVEMENT_TYPES['allocation'][1],
                        'direction': 'adj', 'seq': MOVEMENT_TYPES['allocation'][2],
                        'qty': 0.0, 'value': r['adj_value'],
                    })
        out.sort(key=lambda b: (b['company_name'], b['section'], b['categ_name'], b['code'], b['name'], b['seq']))
        return out

    # ------------------------------------------------------------------
    # Reconciliation & controls
    # ------------------------------------------------------------------
    def _build_reconciliation(self, p, product_info, company_rows, cat_info, sections):
        rec = []
        for company in p['companies']:
            cur = company.currency_id
            # rows of the authoritative valuation that pass the report filters
            auth = {pid: r for (cid, _s, pid), r in company_rows.items() if cid == company.id}
            filtered_ids = []
            for pid in auth:
                ci = cat_info.get((company.id, product_info[pid]['categ_id']), {})
                if p['cost_method'] != 'all' and ci.get('cost_method') != p['cost_method']:
                    continue
                if p['valuation_type'] != 'all' and ci.get('valuation') != p['valuation_type']:
                    continue
                filtered_ids.append(pid)
            report_close = cur.round(float(sum((auth[pid]['close_value'] for pid in filtered_ids), D0)))
            entry = {
                'company_name': company.name,
                'currency': self._currency_info(cur),
                'authoritative_close_value': report_close,
                'checks': [],
                'gl': [],
                'gl_note': '',
            }
            # 1. Independent check against Odoo's own ORM computation
            if p['date_basis'] == 'valuation' and filtered_ids:
                prods = self.env['product.product'].browse(filtered_ids).with_company(company).with_context(
                    to_date=p['end_utc'] - timedelta(seconds=1), active_test=False)
                native = cur.round(sum(prods.mapped('value_svl')))
                entry['checks'].append({
                    'label': _("Odoo native valuation at %s (product.value_svl)", p['date_to']),
                    'report': report_close, 'reference': native, 'difference': cur.round(report_close - native),
                    'ok': cur.is_zero(report_close - native),
                    'note': _("Must be zero: both read the same valuation layers."),
                })
            elif p['date_basis'] == 'accounting':
                entry['checks'].append({
                    'label': _("Odoo native valuation comparison"), 'report': report_close, 'reference': None,
                    'difference': None, 'ok': None,
                    'note': _("Not applicable: report uses journal entry dates; Odoo's native report uses "
                              "valuation layer dates."),
                })
            # 2. Allocated sections vs authoritative valuation
            if p['scope'] != 'company':
                alloc_close = cur.round(sum(s['totals']['close_value'] for s in sections
                                            if s['company_id'] == company.id))
                full_scope = p['scope'] == 'warehouse' and not p.get('warehouse_ids')
                entry['checks'].append({
                    'label': _("Sum of allocated sections vs company valuation"),
                    'report': alloc_close, 'reference': report_close,
                    'difference': cur.round(alloc_close - report_close),
                    'ok': cur.is_zero(alloc_close - report_close) if full_scope else None,
                    'note': _("Allocated values use the company average cost. Differences arise from "
                              "FIFO layer costs, negative stock, consigned stock and stock outside the "
                              "selected scope.") if full_scope else
                    _("Partial scope: the difference is the stock held outside the selected warehouses/locations."),
                })
            # 3. General ledger (automated valuation only)
            self._gl_reconciliation(p, company, auth, filtered_ids, product_info, cat_info, entry)
            rec.append(entry)
        return rec

    def _gl_reconciliation(self, p, company, auth, filtered_ids, product_info, cat_info, entry):
        cur = company.currency_id
        if p.get('product_ids') or p.get('category_ids') or p['cost_method'] != 'all' \
                or not p.get('include_archived', True):
            entry['gl_note'] = _("General ledger comparison is only shown for unfiltered reports "
                                 "(accounts also hold products excluded by the filters).")
            return
        AML = self.env['account.move.line']
        if not AML.has_access('read'):
            entry['gl_note'] = _("General ledger comparison requires accounting read access.")
            return
        by_account = defaultdict(float)
        names = {}
        manual_total = 0.0
        for pid in filtered_ids:
            ci = cat_info.get((company.id, product_info[pid]['categ_id']), {})
            value = float(auth[pid]['close_value'])
            if ci.get('valuation') == 'real_time' and ci.get('account_id'):
                by_account[ci['account_id']] += value
                names[ci['account_id']] = ci['account_name']
            else:
                manual_total += value
        if not by_account:
            entry['gl_note'] = _("No automated (perpetual) valuation categories: inventory is not posted "
                                 "to the general ledger in real time, so there is nothing to reconcile.")
        else:
            groups = AML.with_company(company)._read_group(
                [('account_id', 'in', list(by_account)), ('company_id', '=', company.id),
                 ('parent_state', '=', 'posted'), ('date', '<=', p['date_to'])],
                ['account_id'], ['balance:sum'])
            gl = {acc.id: bal for acc, bal in groups}
            for acc_id, value in sorted(by_account.items(), key=lambda kv: names[kv[0]]):
                value = cur.round(value)
                bal = cur.round(gl.get(acc_id, 0.0))
                entry['gl'].append({'account': names[acc_id], 'inventory_value': value, 'gl_balance': bal,
                                    'difference': cur.round(value - bal), 'ok': cur.is_zero(value - bal)})
            entry['gl_note'] = _(
                "GL balance = posted journal items up to %(date)s. Valuation layers are dated when stock "
                "moves; journal entries may carry another accounting date (e.g. inventory adjustments with "
                "an accounting date, vendor bills, manual entries on the stock account). Differences are "
                "reported, never forced.", date=p['date_to'])
        entry['manual_value'] = cur.round(manual_total)

    def _build_exceptions(self, sections):
        out = []
        for sec in sections:
            for grp in sec['groups']:
                for r in grp['rows']:
                    for code, flag in zip(r['flag_codes'], r['flags']):
                        if code == 'archived':
                            continue
                        out.append({'company_name': sec['company_name'], 'section': sec['label'],
                                    'code': r['code'], 'name': r['name'], 'issue': flag,
                                    'close_qty': r['close_qty'], 'uom': r['uom'],
                                    'close_value': r['close_value'], 'currency': sec['currency']['name']})
        return out

    # ------------------------------------------------------------------
    # Descriptive data
    # ------------------------------------------------------------------
    @api.model
    def _currency_info(self, currency):
        return {'id': currency.id, 'name': currency.name, 'symbol': currency.symbol,
                'position': currency.position, 'digits': currency.decimal_places}

    @api.model
    def _company_info(self, company):
        partner = company.partner_id
        address = [line for line in (partner._display_address(without_company=True) or '').split('\n')
                   if line.strip()]
        return {
            'id': company.id, 'name': company.name, 'address': address,
            'phone': company.phone or '', 'email': company.email or '', 'website': company.website or '',
            'vat': company.vat or '', 'logo': company.logo or False,
            'currency': self._currency_info(company.currency_id),
            'primary_color': company.primary_color or '', 'secondary_color': company.secondary_color or '',
        }

    def _get_meta(self, p, products):
        tz = p['tz_obj']
        now_local = pytz.utc.localize(fields.Datetime.now()).astimezone(tz)
        lang = self.env['res.lang']._get_data(code=self.env.user.lang or 'en_US')
        date_fmt = lang.date_format or '%m/%d/%Y'

        def fdate(d):
            return d.strftime(date_fmt) if d else ''

        filters = [(_('Companies'), ', '.join(p['companies'].mapped('name')))]
        if p['report_type'] == 'period':
            filters.append((_('Period'), '%s – %s' % (fdate(p['date_from']), fdate(p['date_to']))))
        else:
            filters.append((_('Valuation as of'), fdate(p['date_to'])))
        filters.append((_('Date basis'), _('Journal entry (accounting) date') if p['date_basis'] == 'accounting'
                        else _('Inventory valuation date (as Odoo Valuation report)')))
        scope_labels = {'company': _('Company (authoritative)'), 'warehouse': _('Per warehouse (allocated)'),
                        'location': _('Selected locations (allocated)')}
        filters.append((_('Scope'), scope_labels[p['scope']]))
        if p.get('warehouse_ids'):
            filters.append((_('Warehouses'), ', '.join(self.env['stock.warehouse'].browse(p['warehouse_ids']).mapped('name'))))
        if p['scope'] == 'location' or p.get('location_sheets'):
            filters.append((_('Locations'), ', '.join(self.env['stock.location'].browse(p['location_ids']).mapped(
                'complete_name')) if p.get('location_ids') else _('All locations (each with its sub-locations)')))
        if p.get('category_ids'):
            filters.append((_('Product categories'), ', '.join(
                self.env['product.category'].browse(p['category_ids']).mapped('complete_name')) + _(' (incl. sub-categories)')))
        if p.get('product_ids'):
            sel = self.env['product.product'].browse(p['product_ids']).with_context(active_test=False)
            filters.append((_('Products'), ', '.join(sel[:8].mapped('display_name')) +
                            (_(' and %s more', len(sel) - 8) if len(sel) > 8 else '')))
        filters.append((_('Costing method'), {'all': _('All'), 'standard': _('Standard Price'),
                                              'average': _('Average Cost (AVCO)'),
                                              'fifo': _('First In First Out (FIFO)')}[p['cost_method']]))
        filters.append((_('Valuation'), {'all': _('Manual and automated'), 'real_time': _('Automated only'),
                                         'manual_periodic': _('Manual only')}[p['valuation_type']]))
        filters.append((_('Products shown'), {'active': _('With a balance or movement'),
                                              'nonzero': _('Non-zero closing balance only'),
                                              'all': _('All storable products')}[p['stock_filter']]))
        filters.append((_('Archived products'), _('Included') if p.get('include_archived', True) else _('Excluded')))
        return {
            'title': _('Inventory Valuation Report') if p['report_type'] == 'period' else _('Inventory Valuation'),
            'report_type': p['report_type'],
            'scope': p['scope'],
            'allocated': p['scope'] != 'company',
            'date_basis': p['date_basis'],
            'date_from': p['date_from'], 'date_to': p['date_to'],
            'date_from_str': fdate(p['date_from']), 'date_to_str': fdate(p['date_to']),
            'period_label': (_('%(start)s to %(end)s', start=fdate(p['date_from']), end=fdate(p['date_to']))
                             if p['report_type'] == 'period' else _('As of %s', fdate(p['date_to']))),
            'generated_at': now_local.strftime(date_fmt + ' %H:%M'),
            'generated_tz': p['tz'],
            'generated_by': self.env.user.name,
            'filters': filters,
            'detail_level': p['detail_level'],
            'group_by': p['group_by'],
            'qty_digits': self.env['decimal.precision'].precision_get('Product Unit of Measure'),
            'price_digits': self.env['decimal.precision'].precision_get('Product Price'),
            'product_scope_count': len(products),
        }
