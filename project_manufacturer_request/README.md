# Project Manufacturer Request

Odoo 18 custom module that adds a Product Request tab to Project Tasks.

## Flow

Project
→ Task
→ Product Request tab
→ Add Product / Quantity / Unit
→ Submit Manufacturing Request
→ Request becomes Submitted

## Current scope

This first version creates a manufacturing-request workflow and does not
automatically create an `mrp.production` Manufacturing Order.

The next phase can connect submitted request lines to actual Odoo
Manufacturing Orders, BOMs, components, source locations, and procurement.
