{
    "name": "Project Manufacturer Request",
    "version": "18.0.1.2.0",
    "category": "Manufacturing/Project",
    "summary": "Request manufacturing products directly from Project Tasks as a standalone App",
    "description": """
Project Manufacturer Request App
=================================
- Adds a Product Request tab to Project Tasks.
- Submit requests with a stunning Rainbow Success effect.
- Standalone App on the Odoo dashboard to manage all manufacturing requests.
    """,
    "author": "PrimeSoft Technologies",
    "license": "LGPL-3",
    "depends": [
        "project",
        "product",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/project_task_views.xml",
    ],
    "images": [
        "static/description/icon.png",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}