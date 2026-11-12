from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import timedelta

class AccountPaymentInherit(models.Model):
    _inherit = 'account.payment'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            partner_id = vals.get('partner_id')
            if partner_id:
                # Angalia kama mteja ana malipo ya nyuma ya draft au in_process
                unfinished_payment = self.search([
                    ('partner_id', '=', partner_id),
                    ('state', 'in', ['draft', 'in_process'])
                ], limit=1)
                
                if unfinished_payment and unfinished_payment.create_date:
                    # Time limit is set in Settings > Helper Sales > Payment Rules
                    limit, label = self.env['res.config.settings']._get_payment_pending_limit()
                    if (fields.Datetime.now() - unfinished_payment.create_date) > limit:
                        raise UserError(
                            "This customer has a previous payment that is still incomplete, "
                            "and more than %s have passed! "
                            "Please complete the previous payment before creating a new one." % label
                        )
                        
        return super().create(vals_list)

    def write(self, vals):
        """ Hii hukagua kama malipo yamefanyiwa reconciliation kwenye Bank Dashboard ili yabadilike kuwa paid """
        res = super().write(vals)
        for payment in self:
            # Kama malipo yapo 'in_process' na yameunganishwa kikamilifu (reconciled), yabadilishe yawe 'paid'
            if payment.state == 'in_process' and payment.is_reconciled:
                payment.write({'state': 'paid'})
        return res