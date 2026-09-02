# -*- coding: utf-8 -*-

{
    "name": "Helper Sales",
    "version": "18.0.1.0.0",
    "category": "Sales",
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
        "views/sale_order_views.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}