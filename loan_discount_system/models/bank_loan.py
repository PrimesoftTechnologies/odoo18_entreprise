# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class LdsBankLoan(models.Model):
    _name = 'lds.bank.loan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Bank Loan (Treasury)'
    _order = 'loan_date desc, id desc'

    name = fields.Char(string='Loan Name', required=True, tracking=True)
    code = fields.Char(string='Reference', readonly=True, copy=False, default='New')
    company_id = fields.Many2one('res.company', string='Treasury Company', required=True,
                                 default=lambda self: self.env.company, tracking=True)
    currency_id = fields.Many2one(related='company_id.currency_id', store=True)
    bank_id = fields.Many2one('res.partner', string='Bank / Lender', required=True, tracking=True)
    bank_reference = fields.Char(string='Bank Loan Account No.')
    principal = fields.Monetary(string='Amount Borrowed', tracking=True)
    interest_rate = fields.Float(string='Interest Rate (% p.a.)', digits=(12, 4), tracking=True)
    interest_method = fields.Selection([
        ('annuity', 'Reducing balance - equal installments'),
        ('declining', 'Reducing balance - equal principal'),
        ('flat', 'Flat rate'),
    ], string='Interest Method', default='annuity', required=True)
    duration = fields.Integer(string='Duration (months)')
    loan_date = fields.Date(string='Loan Date', default=fields.Date.context_today, required=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'), ('running', 'Running'), ('closed', 'Closed'),
    ], default='draft', tracking=True, copy=False)
    post_entries = fields.Boolean(
        string='Post Accounting Entries', default=True,
        help="Untick if the linked Odoo Loan already posts the accounting entries (avoid double posting).")
    receipt_move_id = fields.Many2one('account.move', string='Loan Receipt Entry', readonly=True, copy=False)
    notes = fields.Text()

    line_ids = fields.One2many('lds.bank.loan.line', 'loan_id', string='Amortization Schedule', copy=False)
    repayment_ids = fields.One2many('lds.bank.loan.repayment', 'loan_id', string='Repayments', copy=False)
    distribution_ids = fields.One2many('lds.loan.distribution', 'loan_id', string='Distributions', copy=False)
    allocation_ids = fields.One2many('lds.allocation', 'loan_id', string='Interest Allocations')

    total_interest = fields.Monetary(compute='_compute_amounts', string='Total Interest')
    paid_principal = fields.Monetary(compute='_compute_amounts', string='Principal Paid')
    paid_interest = fields.Monetary(compute='_compute_amounts', string='Interest Paid')
    outstanding_balance = fields.Monetary(compute='_compute_amounts', string='Outstanding Balance')
    total_distributed = fields.Monetary(compute='_compute_amounts', string='Distributed to Companies')
    undistributed = fields.Monetary(compute='_compute_amounts', string='Kept at Treasury')

    # --- link to the Odoo Loan record ---
    odoo_loan_ref = fields.Reference(selection='_selection_odoo_loan_models', string='Odoo Loan')
    odoo_amount = fields.Monetary(string='Odoo Loan: Amount Borrowed', readonly=True)
    odoo_interest = fields.Monetary(string='Odoo Loan: Interest', readonly=True)
    odoo_outstanding = fields.Monetary(string='Odoo Loan: Outstanding', readonly=True)
    outstanding_difference = fields.Monetary(compute='_compute_amounts', string='Difference vs Odoo Loan')
    last_sync = fields.Datetime(readonly=True)

    @api.model
    def _selection_odoo_loan_models(self):
        models_ = self.env['ir.model'].sudo().search([
            ('model', 'ilike', 'loan'), ('transient', '=', False), ('model', 'not like', 'lds.')],
            order='name')
        return [(m.model, m.name) for m in models_]

    @api.depends('principal', 'line_ids.interest', 'repayment_ids.state',
                 'repayment_ids.principal_amount', 'repayment_ids.interest_amount',
                 'distribution_ids.amount', 'distribution_ids.state',
                 'odoo_outstanding', 'odoo_loan_ref')
    def _compute_amounts(self):
        for loan in self:
            posted = loan.repayment_ids.filtered(lambda r: r.state == 'posted')
            loan.total_interest = sum(loan.line_ids.mapped('interest'))
            loan.paid_principal = sum(posted.mapped('principal_amount'))
            loan.paid_interest = sum(posted.mapped('interest_amount'))
            loan.outstanding_balance = loan.principal - loan.paid_principal
            confirmed = loan.distribution_ids.filtered(lambda d: d.state == 'confirmed')
            loan.total_distributed = sum(confirmed.mapped('amount'))
            loan.undistributed = loan.principal - loan.total_distributed
            loan.outstanding_difference = (
                loan.outstanding_balance - loan.odoo_outstanding if loan.odoo_loan_ref else 0.0)

    @api.constrains('interest_rate', 'principal', 'duration')
    def _check_values(self):
        for loan in self:
            if loan.interest_rate < 0 or loan.principal < 0 or loan.duration < 0:
                raise ValidationError(_("Amount, interest rate and duration cannot be negative."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('code', 'New') == 'New':
                vals['code'] = self.env['ir.sequence'].next_by_code('lds.bank.loan') or 'New'
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Schedule computation
    # ------------------------------------------------------------------
    def action_compute(self):
        for loan in self:
            if loan.state != 'draft':
                raise UserError(_("The schedule can only be computed in Draft state."))
            if loan.principal <= 0 or loan.duration <= 0:
                raise UserError(_("Set the Amount Borrowed and Duration first."))
            cur = loan.currency_id
            P, n = loan.principal, loan.duration
            r = loan.interest_rate / 100.0 / 12.0
            pmt = 0.0
            if loan.interest_method == 'annuity':
                pmt = P / n if not r else P * r / (1 - (1 + r) ** -n)
            balance = P
            vals = []
            for i in range(1, n + 1):
                if loan.interest_method == 'flat':
                    interest = cur.round(P * r)
                    principal = cur.round(P / n)
                elif loan.interest_method == 'annuity':
                    interest = cur.round(balance * r)
                    principal = cur.round(pmt - interest)
                else:
                    interest = cur.round(balance * r)
                    principal = cur.round(P / n)
                if i == n:
                    principal = balance
                balance = cur.round(balance - principal)
                vals.append((0, 0, {
                    'number': i,
                    'date': loan.loan_date + relativedelta(months=i),
                    'principal': principal,
                    'interest': interest,
                    'balance': balance,
                }))
            loan.line_ids.unlink()
            loan.write({'line_ids': vals})
        return True

    def action_upload(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Upload Bank Schedule (Excel)'),
            'res_model': 'lds.loan.upload.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_loan_id': self.id},
        }

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------
    def action_confirm(self):
        for loan in self:
            if loan.state != 'draft':
                continue
            if loan.principal <= 0:
                raise UserError(_("Amount Borrowed must be greater than zero."))
            if not loan.line_ids:
                loan.action_compute()
            if loan.post_entries:
                company = loan.company_id
                cash = company._lds_cash_account()
                loan_acc = company._lds_cfg(['lds_loan_account_id'])['lds_loan_account_id']
                label = _("Bank loan %s", loan.name)
                loan.receipt_move_id = company._lds_post_move(
                    loan.loan_date, label, [
                        (cash, loan.principal, 0.0, label, loan.bank_id),
                        (loan_acc, 0.0, loan.principal, label, loan.bank_id),
                    ])
            loan.state = 'running'
        return True

    def action_close(self):
        for loan in self:
            if loan.currency_id.compare_amounts(loan.outstanding_balance, 0.0) > 0:
                raise UserError(_("Outstanding balance must be zero before closing the loan."))
            loan.state = 'closed'
        return True

    def action_draft(self):
        for loan in self:
            if loan.repayment_ids.filtered(lambda r: r.state == 'posted') or \
                    loan.distribution_ids.filtered(lambda d: d.state == 'confirmed'):
                raise UserError(_("Cannot reset: there are posted repayments or confirmed distributions."))
            if loan.receipt_move_id:
                move = loan.receipt_move_id.sudo()
                move.button_draft()
                move.unlink()
            loan.state = 'draft'
        return True

    def action_generate_allocations(self):
        """Create one interest allocation per (confirmed distribution x schedule line)."""
        Allocation = self.env['lds.allocation']
        for loan in self:
            if loan.principal <= 0:
                continue
            for dist in loan.distribution_ids.filtered(lambda d: d.state == 'confirmed'):
                pct = dist.amount / loan.principal
                cur = loan.currency_id
                existing = dist.allocation_ids.mapped('line_id')
                for line in loan.line_ids - existing:
                    balance_before = line.balance + line.principal
                    Allocation.create({
                        'distribution_id': dist.id,
                        'line_id': line.id,
                        'date': line.date,
                        'principal_share': cur.round(line.principal * pct),
                        'interest_share': cur.round(line.interest * pct),
                        'markup_share': cur.round(balance_before * pct * dist.markup_rate / 100.0 / 12.0),
                    })
        return True

    def action_accrue_all(self):
        for loan in self:
            loan.allocation_ids.filtered(lambda a: a.state == 'draft').action_accrue()
        return True

    # ------------------------------------------------------------------
    # Link with the Odoo Loan record
    # ------------------------------------------------------------------
    def action_sync_odoo_loan(self):
        self.ensure_one()
        rec = self.odoo_loan_ref
        if not rec:
            raise UserError(_("Select the Odoo Loan record first."))
        flds = rec._fields

        def pick(fields_dict, names):
            for n in names:
                if n in fields_dict:
                    return n
            return False

        vals = {'last_sync': fields.Datetime.now()}
        for key, names in (
            ('odoo_amount', ['amount_borrowed', 'amount', 'loan_amount', 'principal', 'borrowed_amount']),
            ('odoo_interest', ['interest', 'interest_amount', 'total_interest']),
            ('odoo_outstanding', ['outstanding_balance', 'outstanding', 'outstanding_amount',
                                  'remaining_amount', 'balance']),
        ):
            fname = pick(flds, names)
            if fname and isinstance(rec[fname], (int, float)):
                vals[key] = rec[fname]
        self.write(vals)

        imported = 0
        if self.state == 'draft' and not self.line_ids:
            imported = self._import_lines_from_odoo_loan(rec)
        self.message_post(body=_("Synchronised with %(model)s: %(name)s (%(n)s schedule lines imported).",
                                 model=rec._description, name=rec.display_name, n=imported))
        return True

    def _import_lines_from_odoo_loan(self, rec):
        for fname, fld in rec._fields.items():
            if fld.type != 'one2many':
                continue
            comodel = self.env[fld.comodel_name]
            cf = comodel._fields
            dname = next((n for n in ('date', 'payment_date', 'due_date') if n in cf), False)
            pname = next((n for n in ('principal', 'principals', 'principal_amount') if n in cf), False)
            iname = next((n for n in ('interest', 'interests', 'interest_amount') if n in cf), False)
            bname = next((n for n in ('outstanding_balance', 'balance', 'outstanding') if n in cf), False)
            if not (dname and pname and iname):
                continue
            vals = []
            for i, l in enumerate(rec[fname].sorted(dname), start=1):
                vals.append((0, 0, {
                    'number': i, 'date': l[dname], 'principal': l[pname], 'interest': l[iname],
                    'balance': l[bname] if bname else 0.0,
                }))
            if vals:
                self.write({'line_ids': vals})
                if not self.principal and self.odoo_amount:
                    self.principal = self.odoo_amount
                if not self.duration:
                    self.duration = len(vals)
                return len(vals)
        return 0
