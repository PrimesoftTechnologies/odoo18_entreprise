from odoo import fields, models

class SaleCar(models.Model):
    _name = 'sale.car'
    _description = 'Sales Car'
    _rec_name = 'name'

    name = fields.Char(string='Car Number', required=True, tracking=True)
    model_name = fields.Char(string='Car Model', tracking=True)


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
    helper_ids = fields.Many2many(
        "hr.employee",
        "sale_order_helper_rel",
        "order_id",
        "employee_id",
        string="Helpers",
        required=True,
        tracking=True,
    )
    # Imebadilishwa kutoka Char kwenda Many2one ya sale.car na kuwekewa tracking
    car_id = fields.Many2one(
        "sale.car",
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