# -*- coding: utf-8 -*-

{
    "name": "Helper Sales",
    "version": "18.0.1.1.1",
    "category": "Sales",
    "sequence": -28,
    "summary": "Add Helper field to Sales Orders",
    "description": """
        Adds a Helper field to Sales Orders.
        The Helper is selected from Employees.
    """,
    "author": "PrimeSoft Technologies",
    "depends": [
        "sale_management",
        "hr",
    ],
    "data": [
        "security/ir.model.access.csv", 
        "views/sale_order_views.xml",
        "reports/invoice_report.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}