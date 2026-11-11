# -*- coding: utf-8 -*-
"""Existing Manufacturing Orders must not be blocked by the new approval flow."""


def migrate(cr, version):
    if not version:
        return
    cr.execute("""
        UPDATE mrp_production SET approval_state = 'cost_approved'
         WHERE state = 'done' AND approval_state = 'draft'
    """)
    cr.execute("""
        UPDATE mrp_production SET approval_state = 'prod_approved'
         WHERE state IN ('confirmed', 'progress', 'to_close') AND approval_state = 'draft'
    """)
