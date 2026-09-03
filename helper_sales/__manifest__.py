# -*- coding: utf-8 -*-

{
    "name": "Helper Sales",
    "version": "18.0.1.1.5",
    "category": "Sales",
    "sequence": -28,
    "summary": "Add Helper field to Sales Orders and Invoices",
    "description": """
        Adds Driver, Helpers, Car Number, and Region fields to Sales Orders and Invoices.
        The fields become read-only once the invoice is confirmed.
    """,
    "author": "PrimeSoft Technologies",
    "depends": [
        "sale_management",
        "hr",
        "account",
    ],
    "data": [
        "security/ir.model.access.csv", 
        "views/sale_order_views.xml",
        "views/account_move_views.xml", 
        "reports/invoice_report.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}