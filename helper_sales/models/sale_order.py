from odoo import fields, models, api
from odoo.exceptions import UserError

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

    def _prepare_invoice(self):
        invoice_vals = super()._prepare_invoice()
        invoice_vals.update({
            'driver_id': self.driver_id.id,
            'helper_ids': [(6, 0, self.helper_ids.ids)],
            'car_id': self.car_id.id,
            'region_id': self.region_id.id,
        })
        return invoice_vals

    def action_view_invoice(self, invoices=False):
        """ Checks if the customer has an incomplete previous payment before allowing Create Invoice """
        for order in self:
            if order.partner_id:
                # Check if the customer has an unfinished payment in draft or in_process state
                unfinished_payment = self.env['account.payment'].search([
                    ('partner_id', '=', order.partner_id.commercial_partner_id.id),
                    ('state', 'in', ['draft', 'in_process'])
                ], limit=1)

                if unfinished_payment:
                    raise UserError(
                        f"This customer ({order.partner_id.name}) has a previous payment that is still incomplete! "
                        "Please complete the previous payment before creating a new invoice."
                    )
        
        return super().action_view_invoice(invoices)