# -*- coding: utf-8 -*-

{
    "name": "Helper Sales",
    "version": "18.0.2.0.0",
    "category": "Sales",
    "sequence": -28,
    "summary": "Logistics, approvals and controls for Sales, Inventory and Accounting",
    "description": """
        - Drivers, Helpers (typed or selected), Car Number and Region on Sales Orders / Invoices
        - Car Number and Analytic Distribution on Internal Transfers
        - Mandatory attachments for Return (delivery) and Credit Note
        - Approval for Physical Inventory counting
        - TIN mandatory for customers and vendors
        - Receipts only from Purchase Orders
        - Update Quantity restricted to one authorised group
        - Automatic Product Internal Reference
    """,
    "author": "PrimeSoft Technologies",
    "depends": [
        "sale_management",
        "sale_stock",
        "purchase",
        "purchase_stock",
        "stock",
        "hr",
        "account",
        "analytic",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "views/sale_order_views.xml",
        "views/account_move_views.xml",
        "views/account_payment_views.xml",
        "views/stock_views.xml",
        "views/partner_views.xml",
        "reports/invoice_report.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
