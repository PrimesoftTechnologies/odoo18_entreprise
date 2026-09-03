from odoo import fields, models

class AccountMove(models.Model):
    _inherit = "account.move"

    driver_id = fields.Many2one(
        "hr.employee",
        string="Driver Name",
        tracking=True,
    )
    helper_ids = fields.Many2many(
        "hr.employee",
        "account_move_helper_rel",
        "move_id",
        "employee_id",
        string="Helpers",
        tracking=True,
    )
    car_number = fields.Char(
        string="Car Number",
        tracking=True,
    )
    region_id = fields.Many2one(
        "sale.region",
        string="Region",
        tracking=True,
    )


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _prepare_invoice(self):
        invoice_vals = super()._prepare_invoice()
        invoice_vals.update({
            'driver_id': self.driver_id.id,
            'helper_ids': [(6, 0, self.helper_ids.ids)],
            'car_number': self.car_number,
            'region_id': self.region_id.id,
        })
        return invoice_vals