{
    "name": "Project Manufacturer Request",
    "version": "18.0.1.3.0",
    "category": "Manufacturing/Project",
    "summary": "Request manufacturing products directly from Project Tasks as a standalone App with Sequence",
    "description": """
Project Manufacturer Request App
================================
- Adds a Product Request tab to Project Tasks.
- Generates a unique sequence number (MR/00001) upon submission.
- Submit requests with a stunning Rainbow Success effect.
- Standalone App on the Odoo dashboard to manage all manufacturing requests.
    """,
    "author": "PrimeSoft Technologies",
    "license": "LGPL-3",
    "depends": [
        "project",
        "product",
        "purchase",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "views/project_task_views.xml",
    ],
    "images": [
        "static/description/icon.png",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}