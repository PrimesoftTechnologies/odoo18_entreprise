from odoo import fields, models

class SaleRegion(models.Model):
    _name = 'sale.region'
    _description = 'Sales Region'
    _rec_name = 'name'

    name = fields.Char(string='Region Name', required=True, tracking=True)
    code = fields.Char(string='Region Code', tracking=True)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    driver_id = fields.Many2one(
        "hr.employee",
        string="Driver Name",
        required=True,
        tracking=True,
    )
    helper_id = fields.Many2one(
        "hr.employee",
        string="Helper",
        required=True,
        tracking=True,
    )
    car_number = fields.Char(
        string="Car Number",
        required=True,
        tracking=True,
    )
    region_id = fields.Many2one(
        "sale.region",
        string="Region",
        required=True,
        tracking=True,
    )