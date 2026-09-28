{
  "name": "Real Estate Construction & Procurement Management",
  "version": "18.0.1.0.0",
  "category": "Real Estate",
  "summary": "Bill of Quantities (BOQ), WBS Breakdown & Material Purchase Requisitions",
  "website": "https://adreaminnovations.odoo.com",
  "description": """
      Manage Work Breakdown Structure (WBS) phases, detailed Bill of Quantities (BOQ) with
      overhead/margin lines, and strict budget purchase requisitions linked to Odoo Purchase Orders.
  """,
  "author": "ADream Innovations",
  "license": "LGPL-3",
  "depends": [
    "ad_estate_base",
    "purchase"
  ],
  "data": [
    "security/ir.model.access.csv",
    "views/estate_boq_views.xml",
    "views/estate_purchase_requisition_views.xml",
    "views/purchase_order_views.xml",
    "views/construction_menus.xml"
  ],
  "demo": [
    "demo/estate_construction_demo.xml"
  ],
  "installable": True,
  "application": False,
  "auto_install": False,
  "images": ["static/description/banner.png"]
}
