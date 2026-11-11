# -*- coding: utf-8 -*-
"""Move the old free-text Driver / Helper names into the new selectable lists."""
import re

from odoo import SUPERUSER_ID, api


def _split(text):
    parts = re.split(r'[,;/&\n]+|\s+and\s+', text or '', flags=re.I)
    return [p.strip() for p in parts if p and p.strip()]


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {"tracking_disable": True, "mail_notrack": True})
    cache = {"sale.driver": {}, "sale.helper": {}}

    def get_id(model, name):
        key = name.lower()
        if key not in cache[model]:
            rec = env[model].with_context(active_test=False).search([("name", "=ilike", name)], limit=1)
            if not rec:
                rec = env[model].create({"name": name})
            cache[model][key] = rec.id
        return cache[model][key]

    for model in ("sale.order", "account.move"):
        records = env[model].search(["|", ("driver_name", "!=", False), ("helper_name", "!=", False)])
        for rec in records:
            vals = {}
            drivers = [get_id("sale.driver", n) for n in _split(rec.driver_name)]
            helpers = [get_id("sale.helper", n) for n in _split(rec.helper_name)]
            if drivers and not rec.driver_ids:
                vals["driver_ids"] = [(4, i) for i in drivers]
            if helpers and not rec.sale_helper_ids:
                vals["sale_helper_ids"] = [(4, i) for i in helpers]
            if vals:
                rec.write(vals)
