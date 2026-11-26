from odoo import _, api, fields, models
from odoo.exceptions import UserError

NON_ACCOUNTING_DISPLAY_TYPES = ('line_section', 'line_subsection', 'line_note')


class AccountAccount(models.Model):
    _inherit = "account.account"

    analytic_account_required = fields.Boolean(
        string="Require Analytic Account",
        default=False,
        help="If checked, any journal item, invoice line, or reconciliation operation using this account requires an Analytic Account.",
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

    @api.model
    def _check_analytic_required_on_lines(self, lines, context_label=""):
        """ Inakagua mistari ya ledger/move na kuzuia kama akaunti yenye analytic_account_required haina analytic """
        missing_lines = lines.filtered(
            lambda line: (
                line.display_type not in NON_ACCOUNTING_DISPLAY_TYPES
                and getattr(line.account_id, 'analytic_account_required', False)
                and not line.analytic_distribution
            )
        )
        if missing_lines:
            names = []
            for acc in missing_lines.mapped('account_id'):
                if acc.display_name not in names:
                    names.append(acc.display_name)
            prefix = f"{context_label} " if context_label else ""
            raise UserError(_(
                "%sAnalytic Account is required for the selected account(s):\n%s"
            ) % (prefix, ", ".join(names)))

    def _check_analytic_required_on_moves(self):
        """ Inazuia ku-post muamala wowote (Journal Entry, Invoice, n.k.) bila Analytic """
        target_moves = self.filtered(
            lambda m: m.move_type in (
                'entry', 'out_invoice', 'out_refund', 'in_invoice', 'in_refund', 'out_receipt', 'in_receipt'
            )
        )
        for move in target_moves:
            self._check_analytic_required_on_lines(move.line_ids)

    def _post(self, soft=True):
        # Kagua attachment kwenye Credit Note (out_refund) wakati wa ku-post
        self._check_credit_note_attachments()

        # Kagua Analytic Account kwenye mistari yote ya ledger kabla ya ku-post
        self._check_analytic_required_on_moves()

        for move in self.filtered(lambda m: m.move_type in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund')):
            move.partner_id.commercial_partner_id._check_tin_required()
        return super()._post(soft=soft)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.onchange('account_id')
    def _onchange_account_id_analytic(self):
        """ Inavuta Analytic Account kutoka kwenye Chart of Account (analytic_account_id) kiotomatiki """
        for line in self:
            if line.account_id and getattr(line.account_id, 'analytic_account_id', False):
                line.analytic_distribution = {str(line.account_id.analytic_account_id.id): 100}
            elif line.account_id and not line.analytic_distribution:
                line.analytic_distribution = False

    @api.constrains('account_id', 'analytic_distribution')
    def _check_analytic_required_bank_statement_lines(self):
        """
        Ngazi ya chini kabisa: inashika mistari ya Manual Operations kwenye Bank Reconciliation
        (mistari ya move ya bank statement line), bila kujali inapitia button gani.
        """
        for line in self:
            move = line.move_id
            if move.state == 'draft':
                continue
            is_statement_move = bool(
                getattr(move, 'statement_line_id', False)
                or getattr(move, 'statement_line_ids', False)
            )
            if not is_statement_move:
                continue
            move._check_analytic_required_on_lines(
                line,
                context_label=_("Bank Reconciliation:"),
            )

    def reconcile(self):
        """ Inakagua pia wakati wa ku-reconcile mistari """
        self.env['account.move']._check_analytic_required_on_lines(
            self,
            context_label=_("Cannot reconcile because"),
        )
        return super().reconcile()


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    def _check_analytic_on_statement_lines(self):
        for st_line in self:
            if st_line.move_id:
                st_line.move_id._check_analytic_required_on_lines(
                    st_line.move_id.line_ids,
                    context_label=_("Bank Reconciliation:"),
                )

    def write(self, vals):
        res = super().write(vals)
        if 'line_ids' in vals or 'is_reconciled' in vals:
            self._check_analytic_on_statement_lines()
        return res


class BankRecWidget(models.Model):
    _inherit = "bank.rec.widget"

    _ANALYTIC_SKIP_FLAGS = (
        'liquidity', 'auto_balance', 'tax_line', 'exchange_diff', 'early_payment',
    )

    def _check_analytic_manual_lines(self):
        """ Inakagua mistari ya Manual Operations kwenye widget kabla ya Validate """
        for widget in self:
            missing_accounts = []
            for rec_line in widget.line_ids:
                if rec_line.flag in self._ANALYTIC_SKIP_FLAGS:
                    continue
                account = rec_line.account_id
                if (
                    account
                    and getattr(account, 'analytic_account_required', False)
                    and not rec_line.analytic_distribution
                    and account.display_name not in missing_accounts
                ):
                    missing_accounts.append(account.display_name)
            if missing_accounts:
                raise UserError(_(
                    "Cannot validate reconciliation because Analytic Account is required for:\n%s"
                ) % ", ".join(missing_accounts))

    def button_validate(self, *args, **kwargs):
        self._check_analytic_manual_lines()
        return super().button_validate(*args, **kwargs)

    # Methods zifuatazo zitaitwa tu kama zipo kwenye version yako ya Odoo
    # (kama hazipo kwenye parent, hazitaitwa kamwe, kwa hiyo ni salama).
    def js_action_validate(self, *args, **kwargs):
        self._check_analytic_manual_lines()
        return super().js_action_validate(*args, **kwargs)

    def _action_validate(self, *args, **kwargs):
        self._check_analytic_manual_lines()
        return super()._action_validate(*args, **kwargs)