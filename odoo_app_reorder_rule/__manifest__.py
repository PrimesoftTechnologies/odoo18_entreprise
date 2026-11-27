{
    "name": "Odoo App Reorder Rule Alerts",
    "version": "18.0.1.0.0",
    "category": "Inventory/Inventory",
    "summary": "Alert in Odoo and outside Odoo (browser notification, tab/app badge, email) when on-hand stock falls below the Reorder Rule minimum.",
    "description": """
When the On Hand quantity of a product falls below the Minimum of its
Reorder Rule (Inventory > Operations > Replenishment), this module:

* shows a pop-up alert inside Odoo (live, no page refresh needed)
* shows a bell icon with a red counter in the Odoo top bar
* shows a badge on the browser tab icon / installed app icon
* shows a desktop (browser) notification even if you are on another tab/window
* sends an Inbox/Email message to the Reorder Alert Receivers
* keeps a list of alerts: Inventory > Reorder Alerts
    """,
    "author": "Custom",
    "license": "LGPL-3",
    "depends": ["stock", "mail", "bus"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/reorder_alert_views.xml",
        "data/ir_cron.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "odoo_app_reorder_rule/static/src/js/reorder_alert_service.js",
            "odoo_app_reorder_rule/static/src/js/reorder_alert_systray.js",
            "odoo_app_reorder_rule/static/src/xml/reorder_alert_systray.xml",
            "odoo_app_reorder_rule/static/src/scss/reorder_alert.scss",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
