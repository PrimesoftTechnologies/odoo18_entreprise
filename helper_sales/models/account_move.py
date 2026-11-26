from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountAccount(models.Model):
    _inherit = "account.account"

    analytic_account_required = fields.Boolean(
        string="Require Analytic Account on Invoice",
        default=False,
        help="If checked, invoices using this account cannot be confirmed/posted without an Analytic Account.",
    )


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
        string="Drivers", tracking=True,
    )
    sale_helper_ids = fields.Many2many(
        "sale.helper", "account_move_sale_helper_rel", "move_id", "helper_id",
        string="Helpers", tracking=True,
    )
    car_id = fields.Many2one("sale.car", string="Car Number", tracking=True)
    region_id = fields.Many2one("sale.region", string="Region", tracking=True)

    # Sharti la kuangalia kama mtumiaji yuko kwenye list ya Reviewers
    can_review = fields.Boolean(compute='_compute_can_review')

    @api.depends('company_id.account_reviewer_ids')
    def _compute_can_review(self):
        for move in self:
            reviewers = move.company_id.account_reviewer_ids
            if not reviewers:
                move.can_review = True
            else:
                move.can_review = self.env.user in reviewers

    # Kuongeza 'reviewed' moja kwa moja kwenye state ya asili ya Odoo
    state = fields.Selection(
        selection_add=[('reviewed', 'Reviewed')],
        ondelete={'reviewed': 'set default'}
    )

    def action_review(self):
        """ Inabadilisha state kutoka 'posted' kwenda 'reviewed' baada ya ukaguzi """
        for move in self:
            reviewers = move.company_id.account_reviewer_ids
            if reviewers and self.env.user not in reviewers:
                raise UserError(_("You are not authorized to review this entry. Please contact your administrator."))
            move.state = 'reviewed'
        return True

    def button_draft(self):
        """ Huruhusu Reset to Draft kufanya kazi hata kama entry ipo 'reviewed' """
        reviewed_moves = self.filtered(lambda m: m.state == 'reviewed')
        if reviewed_moves:
            reviewed_moves.write({'state': 'posted'})
        return super().button_draft()

    def action_reverse(self):
        """ Huruhusu Credit Note / Reverse Entry kufanya kazi hata kama entry ipo 'reviewed' """
        reviewed_moves = self.filtered(lambda m: m.state == 'reviewed')
        if reviewed_moves:
            reviewed_moves.write({'state': 'posted'})
        return super().action_reverse()

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
        """ Inakagua kama Credit Note ina attachments kabla ya kuifanya Posted """
        for move in self.filtered(lambda m: m.move_type == 'out_refund'):
            if not move._get_manual_attachments():
                raise UserError(_(
                    "Please attach the Delivery Slip signed with the customer and the "
                    "Return Documents from the Inventory person before posting this Credit Note."
                ))

    def _check_analytic_required_on_invoices(self):
        """ Inazuia kuthibitisha/ku-post Invoice kama Chart of Account ina analytic_account_required na Analytic haijajazwa """
        invoice_moves = self.filtered(
            lambda m: m.move_type in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund')
        )
        for move in invoice_moves:
            missing_lines = move.invoice_line_ids.filtered(
                lambda line: (
                    line.display_type == 'product'
                    and getattr(line.account_id, 'analytic_account_required', False)
                    and not line.analytic_distribution
                )
            )
            if missing_lines:
                line_labels = ", ".join(
                    missing_lines.mapped('product_id.display_name')
                    or missing_lines.mapped('name')
                    or missing_lines.mapped('account_id.display_name')
                )
                raise UserError(_(
                    "Cannot confirm/post this invoice because Analytic Account is required for the selected account(s) on:\n%s"
                ) % line_labels)

    def _post(self, soft=True):
        # Kagua attachment kwenye Credit Note (out_refund) wakati wa ku-post
        self._check_credit_note_attachments()

        # Kagua Analytic Account kwenye mistari ya Invoice kulingana na mipangilio ya Chart of Account
        self._check_analytic_required_on_invoices()

        for move in self.filtered(lambda m: m.move_type in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund')):
            move.partner_id.commercial_partner_id._check_tin_required()
        return super()._post(soft=soft)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.onchange('account_id')
    def _onchange_account_id_analytic(self):
        """ Inavuta Analytic Account kutoka kwenye Chart of Account (analytic_account_id) kiotomatiki """
        for line in self:
            if line.account_id and hasattr(line.account_id, 'analytic_account_id') and line.account_id.analytic_account_id:
                line.analytic_distribution = {str(line.account_id.analytic_account_id.id): 100}
            elif line.account_id and not line.analytic_distribution:
                line.analytic_distribution = False