{
    "name": "Van Management System",
    "version": "18.0.1.0.0",
    "category": "Sales",
    "sequence": -19,

    "summary": "Professional van distribution, route, sales and stock management",

    "description": """
Van Management System for Odoo 18.

Features:
- Van master data linked to Fleet
- Dedicated stock location per van
- Van POS configuration
- Van route planning and management
- Route assignment to vans and salesmen
- Customer assignment to routes
- Route scheduling and status tracking
- Load requests with supervisor approval
- Unload requests with supervisor approval
- Retirement Route management
- Company-based Van Transfer Approvers
- Approved Quantity controlled by assigned approvers
- Sales management
- Sales by Route
- Sales by Salesman
- Sales Reports
- Stock movements powered by Odoo Inventory
- Salesman access restrictions
- Van stock management
- Real-time stock validation support
- Integration with Sales, Point of Sale, Inventory and Fleet
""",

    "author": "PrimeSoft Technologies",
    "license": "LGPL-3",

    "depends": [
        "stock",
        "sale_management",
        "point_of_sale",
        "fleet",
        "mail",
    ],

    "data": [

        # ======================================================
        # SECURITY
        # ======================================================

        "security/security.xml",
        "security/ir.model.access.csv",

        # ======================================================
        # DATA
        # ======================================================

        "data/stock_data.xml",
        "data/sequence_data.xml",
        "data/route_sequence.xml",

        # ======================================================
        # VIEWS
        # ======================================================

        "views/res_company_views.xml",
        "views/van_vehicle_views.xml",
        "views/van_transfer_views.xml",
        "views/van_route_views.xml",
        "views/van_route_complete_wizard_views.xml",
        "views/van_retirement_route_views.xml",

        # ======================================================
        # SALES
        # ======================================================

        "views/van_sales_views.xml",

        # ======================================================
        # POINT OF SALE
        # ======================================================

        "views/pos_config_views.xml",
        "views/van_configuration_views.xml",

        # ======================================================
        # MENUS
        # ======================================================

        "views/menus.xml",
    ],

    "images": [
        "static/description/icon.png",
    ],

    "installable": True,
    "application": True,
}