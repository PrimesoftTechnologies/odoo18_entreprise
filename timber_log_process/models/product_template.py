from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    timber_type = fields.Selection(
        [
            ("log", "Timber Log (raw material)"),
            ("board", "Finished Timber / Boards"),
            ("waste", "Sawing Waste (by-product)"),
        ],
        string="Timber Role",
        help="Marks the product as part of the timber process. Used by the "
             "timber measurement tabs, reports and menus.",
    )
