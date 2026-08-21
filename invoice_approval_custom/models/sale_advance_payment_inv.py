from odoo import models

class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

   
    def _create_invoices(self, sale_orders):
        return super()._create_invoices(sale_orders)