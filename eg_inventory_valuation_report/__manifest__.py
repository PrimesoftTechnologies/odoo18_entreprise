{
    "name": "Inventory Valuation Report",
    "version": "18.0.18.33.0",
    "category": "Inventory/Inventory",
    "summary": "Audit-ready inventory valuation report (PDF & Excel) reconciled with Odoo stock valuation "
               "layers: opening, incoming, outgoing, adjustments and closing per product, category, "
               "company and warehouse.",
    "description": """
Inventory Valuation Report
==========================

* Opening / incoming / outgoing / valuation adjustments / closing, for any period or as of a date.
* Figures read from Odoo's stock valuation layers (Standard, AVCO, FIFO; manual and automated valuation),
  including landed costs, revaluations, price differences and negative-stock corrections.
* Built-in controls: native Odoo valuation check, general ledger comparison for automated valuation,
  exceptions (negative stock, value without quantity, ...).
* Multi-company (per-currency totals), per-warehouse and per-location views (clearly marked as allocations).
* Premium PDF (landscape) and Excel workbook (summary, detail, movement breakdown, reconciliation,
  methodology) generated from one shared dataset.

See doc/TECHNICAL.md for the methodology.
""",
    "author": "INKERP",
    "website": "https://www.inkerp.com",
    "depends": [
        "stock_account",
        "sale_management",
        "purchase",
    ],
    "external_dependencies": {"python": ["xlsxwriter"]},
    "data": [
        "security/ir.model.access.csv",
        "reports/inventory_valuation_pdf_report.xml",
        "wizard/inventory_valuation_report_views.xml",
    ],
    "images": [
        "static/description/banner.gif"
    ],
    "license": "OPL-1",
    "installable": True,
    "application": True,
    "auto_install": False,
    "price": "19.0",
    "currency": "EUR"
}
