# -*- coding: utf-8 -*-
"""Controlled-scenario tests for the inventory valuation report.

Every scenario builds dated stock operations, then checks the report against
(1) figures calculated by hand in the test, (2) Odoo's native valuation
(``product.value_svl`` at date) and (3) the reconciliation identities.

Dates are applied by re-stamping the records created by each operation
(valuation layers, moves, move lines, journal entries), which is how a
real history looks in the database.
"""
import base64
import io
from contextlib import contextmanager
from datetime import datetime, timedelta

from odoo import Command, fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import Form, tagged

from freezegun import freeze_time

from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import \
    ValuationReconciliationTestCommon



class IvrTestCommon(ValuationReconciliationTestCommon):
    """Shared fixtures and dated stock operations for the report tests (no tests here)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.groups_id += cls.env.ref('stock.group_stock_manager')
        cls.env.user.tz = 'UTC'
        cls.company = cls.env.company
        cls.wh = cls.env['stock.warehouse'].search([('company_id', '=', cls.company.id)], limit=1)
        cls.stock = cls.wh.lot_stock_id
        cls.shelf = cls.env['stock.location'].create({'name': 'Shelf IVR', 'location_id': cls.stock.id,
                                                      'usage': 'internal'})
        cls.wh2 = cls.env['stock.warehouse'].create({'name': 'IVR WH2', 'code': 'IVR2',
                                                     'company_id': cls.company.id})
        cls.supplier = cls.env.ref('stock.stock_location_suppliers')
        cls.customer = cls.env.ref('stock.stock_location_customers')
        cls.inventory_loss = cls.env['stock.location'].search([
            ('usage', '=', 'inventory'), ('company_id', 'in', [cls.company.id, False]),
            ('scrap_location', '=', False)], limit=1)
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')
        cls.uom_dozen = cls.env.ref('uom.product_uom_dozen')
        cls.cat_avco = cls._categ('IVR AVCO', 'average')
        cls.cat_fifo = cls._categ('IVR FIFO', 'fifo')
        cls.cat_std = cls._categ('IVR STD', 'standard')
        cls.cat_auto_avco = cls._categ('IVR AUTO AVCO', 'average', real_time=True)

    @classmethod
    def _categ(cls, name, method, real_time=False):
        vals = {'name': name, 'property_cost_method': method,
                'property_valuation': 'real_time' if real_time else 'manual_periodic'}
        if real_time:
            vals.update({
                'property_stock_valuation_account_id': cls.company_data['default_account_stock_valuation'].id,
                'property_stock_account_input_categ_id': cls.company_data['default_account_stock_in'].id,
                'property_stock_account_output_categ_id': cls.company_data['default_account_stock_out'].id,
                'property_stock_journal': cls.company_data['default_journal_misc'].id,
            })
        return cls.env['product.category'].create(vals)

    def _product(self, code, categ, cost=0.0, **kw):
        return self.env['product.product'].create(dict({
            'name': 'Product %s' % code, 'default_code': code, 'is_storable': True,
            'categ_id': categ.id, 'standard_price': cost}, **kw))

    # ------------------------------------------------------------------
    # dated operations
    # ------------------------------------------------------------------
    def _max_ids(self):
        self.env.flush_all()
        res = {}
        for table in ('stock_valuation_layer', 'stock_move', 'stock_move_line', 'account_move'):
            self.env.cr.execute('SELECT COALESCE(MAX(id), 0) FROM %s' % table)
            res[table] = self.env.cr.fetchone()[0]
        return res

    @contextmanager
    def _at(self, when):
        """Stamp every valuation layer / move / move line / journal entry created in the block."""
        before = self._max_ids()
        ts = datetime.strptime(when, '%Y-%m-%d %H:%M:%S')
        # freeze_time gives journal entries a consistent date and sequence;
        # layers/moves are re-stamped because the cursor caches its 'now'.
        with freeze_time(ts):
            yield
            self.env.flush_all()
        cr = self.env.cr
        cr.execute('UPDATE stock_valuation_layer SET create_date=%s WHERE id > %s', (ts, before['stock_valuation_layer']))
        cr.execute('UPDATE stock_move SET date=%s WHERE id > %s AND state = %s', (ts, before['stock_move'], 'done'))
        cr.execute('UPDATE stock_move_line SET date=%s WHERE id > %s AND state = %s', (ts, before['stock_move_line'], 'done'))
        self.env.invalidate_all()

    def _move(self, product, qty, src, dst, when, price=None, uom=None, company=None, owner=None, lot=None,
              lot_name=None, origin_move=None):
        company = company or self.company
        env = self.env(context=dict(self.env.context, allowed_company_ids=[company.id]))
        uom = uom or product.uom_id
        with self._at(when):
            vals = {'name': 'ivr', 'product_id': product.id, 'product_uom_qty': qty, 'product_uom': uom.id,
                    'location_id': src.id, 'location_dest_id': dst.id, 'company_id': company.id}
            if price is not None:
                vals['price_unit'] = price
            if origin_move:
                vals['origin_returned_move_id'] = origin_move.id
            move = env['stock.move'].create(vals)
            move._action_confirm()
            move._action_assign()
            move.move_line_ids.unlink()
            ml_vals = {'move_id': move.id, 'product_id': product.id, 'product_uom_id': uom.id,
                       'location_id': src.id, 'location_dest_id': dst.id, 'quantity': qty,
                       'company_id': company.id}
            if owner:
                ml_vals['owner_id'] = owner.id
            if lot:
                ml_vals['lot_id'] = lot.id
            if lot_name:
                ml_vals['lot_name'] = lot_name
            env['stock.move.line'].create(ml_vals)
            move.picked = True
            move._action_done()
        return move

    def _in(self, product, qty, price, when, dst=None, **kw):
        return self._move(product, qty, self.supplier, dst or self.stock, when, price=price, **kw)

    def _out(self, product, qty, when, src=None, dst=None, **kw):
        return self._move(product, qty, src or self.stock, dst or self.customer, when, **kw)
