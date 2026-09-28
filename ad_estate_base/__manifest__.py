{
  "name": "Real Estate Base Foundation",
  "version": "18.0.1.0.0",
  "category": "Real Estate",
  "summary": "Master Models, Property Inventory Spectrum & Command Nexus Dashboard",
  "website": "https://adreaminnovations.odoo.com",
  "description": """
      Manage master real estate projects, building wings, property units, unit types,
      amenities, and executive operational dashboards from a single, unified database.
  """,
  "author": "ADream Innovations",
  "license": "LGPL-3",
  "depends": [
    "base",
    "mail",
    "account",
    "analytic",
    "contacts"
  ],
  "data": [
    "security/estate_security.xml",
    "security/ir.model.access.csv",
    "views/estate_dashboard_views.xml",
    "views/estate_project_views.xml",
    "views/estate_building_views.xml",
    "views/estate_unit_views.xml",
    "views/res_partner_views.xml",
    "views/estate_menus.xml"
  ],
  "assets": {
    "web.assets_backend": [
      "ad_estate_base/static/src/components/estate_dashboard.xml",
      "ad_estate_base/static/src/components/estate_dashboard.js"
    ]
  },
  "demo": [
    "demo/estate_base_demo.xml"
  ],
  "installable": True,
  "application": True,
  "auto_install": False,
  "images": ["static/description/banner.png"]
}
