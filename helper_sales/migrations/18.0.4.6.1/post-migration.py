# -*- coding: utf-8 -*-
"""Remove the 'Unknown' brand / model placeholders: vehicles keep only their plate number."""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    try:
        with cr.savepoint():
            _clean(cr)
    except Exception:
        _logger.exception("helper_sales: cleaning the 'Unknown' vehicle model failed")


def _clean(cr):
    env = api.Environment(cr, SUPERUSER_ID, {"tracking_disable": True, "mail_notrack": True})
    models = env["fleet.vehicle.model"].search([("name", "=", "Unknown"), ("brand_id.name", "=", "Unknown")])
    if not models:
        return
    vehicles = env["fleet.vehicle"].with_context(active_test=False).search([("model_id", "in", models.ids)])
    vehicles.write({"model_id": False})
    brands = models.brand_id
    models.unlink()
    for brand in brands:
        if not env["fleet.vehicle.model"].search_count([("brand_id", "=", brand.id)]):
            brand.unlink()
