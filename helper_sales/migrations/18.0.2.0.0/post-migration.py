# -*- coding: utf-8 -*-
"""Copy old Driver / Helper (hr.employee) values into the new Driver / Helper lists."""
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {"tracking_disable": True, "mail_notrack": True})

    def get_or_create(model, employee, cache):
        if employee.id not in cache:
            rec = env[model].with_context(active_test=False).search([("name", "=", employee.name)], limit=1)
            if not rec:
                rec = env[model].create({"name": employee.name, "employee_id": employee.id})
            cache[employee.id] = rec.id
        return cache[employee.id]

    drivers, helpers = {}, {}
    for model in ("sale.order", "account.move"):
        records = env[model].search(["|", ("driver_id", "!=", False), ("helper_ids", "!=", False)])
        for rec in records:
            vals = {}
            if rec.driver_id:
                vals["driver_ids"] = [(4, get_or_create("sale.driver", rec.driver_id, drivers))]
            if rec.helper_ids:
                vals["sale_helper_ids"] = [
                    (4, get_or_create("sale.helper", emp, helpers)) for emp in rec.helper_ids
                ]
            if vals:
                rec.write(vals)
