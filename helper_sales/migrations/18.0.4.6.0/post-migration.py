# -*- coding: utf-8 -*-
"""Copy the old cars (sale.car) into Fleet and link existing orders / invoices / transfers to them."""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    try:
        with cr.savepoint():
            _copy_cars(cr)
    except Exception:  # never block the upgrade because of old data
        _logger.exception("helper_sales: copying old cars into Fleet failed")


def _copy_cars(cr):
    env = api.Environment(cr, SUPERUSER_ID, {"tracking_disable": True, "mail_notrack": True})
    cars = env["sale.car"].search([])
    if not cars:
        return
    Vehicle = env["fleet.vehicle"].with_context(active_test=False)
    for car in cars:
        vehicle = Vehicle.search([("license_plate", "=ilike", car.name)], limit=1) \
            or Vehicle.create({"license_plate": car.name})
        for table in ("sale_order", "account_move", "stock_picking"):
            cr.execute(
                "UPDATE %s SET vehicle_id = %%s WHERE car_id = %%s AND vehicle_id IS NULL" % table,
                (vehicle.id, car.id),
            )
