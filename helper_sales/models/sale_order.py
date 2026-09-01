# -*- coding: utf-8 -*-

from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    helper_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Helper",
        tracking=True,
    )