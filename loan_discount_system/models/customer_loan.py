# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class LdsCustomerLoan(models.Model):
    _name = 'lds.customer.loan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Loan Distributed to a Customer (Discount Center)'
    _order = 'date desc, id desc'

    name = fields.Char(string='Loan Name', required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, tracking=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id', store=True)
    amount = fields.Monetary(string='Amount Borrowed', tracking=True)
    interest = fields.Monetary(string='Interest', tracking=True)
    outstanding_balance = fields.Monetary(string='Outstanding Balance', compute='_compute_amounts')
    paid_principal = fields.Monetary(compute='_compute_amounts', string='Principal Paid')
    paid_interest = fields.Monetary(compute='_compute_amounts', string='Interest Paid')
    date = fields.Date(string='Loan Date', required=True, default=fields.Date.context_today, tracking=True)
    duration = fields.Integer(string='Duration', tracking=True)
    state = fields.Selection([('draft', 'Draft'), ('running', 'Running'), ('closed', 'Closed')],
                             default='draft', tracking=True, copy=False)
    line_ids = fields.One2many('lds.customer.loan.line', 'loan_id', string='Amortization schedule', copy=False)

    # ----- Loan Settings -----
    odoo_loan_model = fields.Char(string='Bank Loan Model', default=lambda self: self._default_loan_model(),
                                  copy=True)
    odoo_loan_id = fields.Many2oneReference(string='Bank Loan', model_field='odoo_loan_model', tracking=True,
                                            help="The loan registered in Accounting > Loans that gives the money.")
    odoo_loan_amount = fields.Monetary(compute='_compute_odoo_loan', string='Bank Loan Amount')
    loan_distributed = fields.Monetary(compute='_compute_odoo_loan', string='Already Distributed (others)')
    loan_available = fields.Monetary(compute='_compute_odoo_loan', string='Still Available')
    journal_id = fields.Many2one(
        'account.journal', string='Journal',
        domain="[('company_id', '=', company_id), ('type', 'in', ('bank', 'cash'))]",
        default=lambda self: self.env.company.lds_journal_id)
    post_entries = fields.Boolean(string='Post Accounting Entries', default=True)
    move_id = fields.Many2one('account.move', string='Disbursement Entry', readonly=True, copy=False)
    notes = fields.Text()

    @api.model
    def _default_loan_model(self):
        """Find the model behind Accounting > Loans.

        1. system parameter 'lds.loan_model' (manual override)
        2. the model that owns a field labelled 'Amount Borrowed'
        3. a model with 'loan' in its name that has an 'outstanding_balance' field
        """
        param = self.env['ir.config_parameter'].sudo().get_param('lds.loan_model')
        if param and param in self.env:
            return param
        Field = self.env['ir.model.fields'].sudo().with_context(lang='en_US')
        found = Field.search([('field_description', '=', 'Amount Borrowed'),
                              ('model', 'not like', 'lds.')], order='id')
        for rec in found:
            if rec.model in self.env:
                return rec.model
        found = Field.search([('name', '=', 'outstanding_balance'), ('model', 'ilike', 'loan'),
                              ('model', 'not like', 'lds.')], order='id')
        for rec in found:
            if rec.model in self.env:
                return rec.model
        return False

    def _get_bank_loan(self):
        self.ensure_one()
        model = self.odoo_loan_model
        if not (model and self.odoo_loan_id and model in self.env):
            return False
        return self.env[model].sudo().browse(self.odoo_loan_id).exists()

    @api.depends('amount', 'line_ids.status', 'line_ids.principal', 'line_ids.interest')
    def _compute_amounts(self):
        for loan in self:
            paid = loan.line_ids.filtered(lambda l: l.status == 'paid')
            loan.paid_principal = sum(paid.mapped('principal'))
            loan.paid_interest = sum(paid.mapped('interest'))
            loan.outstanding_balance = loan.amount - loan.paid_principal

    def _get_odoo_loan_amount(self):
        self.ensure_one()
        rec = self._get_bank_loan()
        if not rec:
            return 0.0
        for fname in ('amount_borrowed', 'amount', 'loan_amount', 'principal', 'borrowed_amount'):
            if fname in rec._fields and isinstance(rec[fname], (int, float)):
                return rec[fname]
        return 0.0

    @api.depends('odoo_loan_model', 'odoo_loan_id', 'amount', 'state')
    def _compute_odoo_loan(self):
        for loan in self:
            total = loan._get_odoo_loan_amount()
            others = 0.0
            if loan.odoo_loan_id:
                domain = [('odoo_loan_model', '=', loan.odoo_loan_model),
                          ('odoo_loan_id', '=', loan.odoo_loan_id), ('state', '!=', 'draft')]
                if loan._origin.id:
                    domain.append(('id', '!=', loan._origin.id))
                others = sum(self.sudo().search(domain).mapped('amount'))
            loan.odoo_loan_amount = total
            loan.loan_distributed = others
            loan.loan_available = total - others if total else 0.0

    @api.constrains('amount', 'interest', 'duration')
    def _check_values(self):
        for loan in self:
            if loan.amount < 0 or loan.interest < 0 or loan.duration < 0:
                raise ValidationError(_("Amount, interest and duration cannot be negative."))

    @api.onchange('company_id')
    def _onchange_company_id(self):
        self.journal_id = self.company_id.lds_journal_id

    def _lds_journal(self):
        self.ensure_one()
        journal = self.journal_id or self.company_id.sudo().lds_journal_id
        if not journal:
            raise UserError(_("Select the Journal in the Loan Settings tab."))
        if not journal.default_account_id:
            raise UserError(_("Journal '%s' has no default account.", journal.name))
        return journal

    # ------------------------------------------------------------------
    # Buttons
    # ------------------------------------------------------------------
    def action_compute(self):
        """Spread the Amount Borrowed and the Interest equally over the Duration (months)."""
        for loan in self:
            if loan.state != 'draft':
                raise UserError(_("The schedule can only be computed in Draft state."))
            if loan.amount <= 0 or loan.duration <= 0:
                raise UserError(_("Enter the Amount Borrowed and the Duration first."))
            cur, n = loan.currency_id, loan.duration
            p_each, i_each = cur.round(loan.amount / n), cur.round(loan.interest / n)
            p_left, i_left, balance = loan.amount, loan.interest, loan.amount
            vals = []
            for i in range(1, n + 1):
                principal = p_left if i == n else p_each
                interest = i_left if i == n else i_each
                p_left, i_left = cur.round(p_left - principal), cur.round(i_left - interest)
                balance = cur.round(balance - principal)
                vals.append((0, 0, {
                    'number': i, 'date': loan.date + relativedelta(months=i),
                    'principal': principal, 'interest': interest, 'balance': balance,
                }))
            loan.line_ids.unlink()
            loan.write({'line_ids': vals})
        return True

    def action_upload(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Upload Schedule (Excel)'),
            'res_model': 'lds.customer.loan.upload',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_loan_id': self.id},
        }

    def action_confirm(self):
        for loan in self:
            if loan.state != 'draft':
                continue
            if loan.amount <= 0:
                raise UserError(_("Amount Borrowed must be greater than zero."))
            if loan.odoo_loan_model and not loan.odoo_loan_id:
                raise UserError(_("Select the Bank Loan (from Accounting > Loans) that gives this money."))
            if not loan.line_ids:
                loan.action_compute()
            total_principal = sum(loan.line_ids.mapped('principal'))
            if loan.currency_id.compare_amounts(total_principal, loan.amount) != 0:
                raise UserError(_("The schedule principals (%(p)s) differ from the Amount Borrowed (%(a)s).",
                                  p=total_principal, a=loan.amount))
            if loan.odoo_loan_id and loan.odoo_loan_amount and \
                    loan.currency_id.compare_amounts(loan.amount, loan.loan_available) > 0:
                raise UserError(_("Only %(av)s is still available on the bank loan (amount %(tot)s).",
                                  av=loan.loan_available, tot=loan.odoo_loan_amount))
            if loan.post_entries:
                company = loan.company_id
                journal = loan._lds_journal()
                receivable = company._lds_receivable(loan.partner_id)
                label = _("Loan %(n)s given to %(c)s", n=loan.name, c=loan.partner_id.name)
                # Dr Customer receivable / Cr Bank
                loan.move_id = company._lds_post_move(journal, loan.date, label, [
                    (receivable, loan.amount, 0.0, label, loan.partner_id),
                    (journal.default_account_id, 0.0, loan.amount, label, loan.partner_id),
                ])
            loan.state = 'running'
        return True

    def action_draft(self):
        for loan in self:
            if loan.line_ids.filtered(lambda l: l.status == 'paid'):
                raise UserError(_("Cannot reset: some installments are already paid."))
            if loan.move_id:
                move = loan.move_id.sudo()
                move.button_draft()
                move.unlink()
            loan.state = 'draft'
        return True

    @api.model
    def _lds_restore_legacy_loans(self):
        from ..hooks import restore_legacy
        restore_legacy(self.env)
        return True
