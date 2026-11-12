
from odoo import _, fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    # Legacy fields (kept so old data is not lost)
    driver_id = fields.Many2one("hr.employee", string="Driver (Old)")
    helper_ids = fields.Many2many(
        "hr.employee", "account_move_helper_rel", "move_id", "employee_id",
        string="Helpers (Old)",
    )

    driver_name = fields.Char(string="Driver (Old Text)")
    helper_name = fields.Char(string="Helper (Old Text)")

    driver_ids = fields.Many2many(
        "sale.driver", "account_move_sale_driver_rel", "move_id", "driver_id",
        string="Drivers", tracking=True, domain=[('is_external', '=', False)],
    )
    sale_helper_ids = fields.Many2many(
        "sale.helper", "account_move_sale_helper_rel", "move_id", "helper_id",
        string="Helpers", tracking=True, domain=[('is_external', '=', False)],
    )
    car_id = fields.Many2one("sale.car", string="Car Number", tracking=True)
    region_id = fields.Many2one("sale.region", string="Region", tracking=True)

    def _get_manual_attachments(self):
        """ Attachments uploaded by users (not the auto-generated invoice PDF). """
        self.ensure_one()
        attachments = self.env['ir.attachment'].sudo().search([
            ('res_model', '=', 'account.move'),
            ('res_id', '=', self.id),
            ('res_field', '=', False),
        ])
        pdf_id = self.invoice_pdf_report_id.id if 'invoice_pdf_report_id' in self._fields else False
        prefix = (self.name or '').replace('/', '_')

        def _is_manual(att):
            if pdf_id and att.id == pdf_id:
                return False
            if prefix and prefix != '/' and (att.name or '').startswith(prefix):
                return False
            return True

        return attachments.filtered(_is_manual)

    def _check_credit_note_attachments(self):
        for move in self.filtered(lambda m: m.move_type == 'out_invoice'):
            if not move._get_manual_attachments():
                raise UserError(_(
                    "Please attach the Delivery Slip signed with the customer and the "
                    "Return Documents from the Inventory person before creating a Credit Note."
                ))

    def _post(self, soft=True):
        for move in self.filtered(lambda m: m.move_type in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund')):
            move.partner_id.commercial_partner_id._check_tin_required()
        return super()._post(soft=soft)
