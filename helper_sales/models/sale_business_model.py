# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SaleBusinessModel(models.Model):
    _name = 'sale.business.model'
    _description = 'Business Model'
    _order = 'name'

    name = fields.Char(string='Business Name', required=True)
    code = fields.Char(string='Short Code', required=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        help="Only users working in this company see this Business Line.",
    )
    journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        domain="[('company_id', '=', company_id), ('type', '=', 'sale')]",
        help="Sales Journal automatically applied when creating a customer invoice for this Business Line.",
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('code_company_uniq', 'unique(code, company_id)', 'The Short Code must be unique per Company.'),
    ]

    @api.constrains('code')
    def _check_code(self):
        for rec in self:
            if not rec.code or '/' in rec.code or ' ' in rec.code:
                raise ValidationError(_("The Short Code cannot contain spaces or '/'."))

    @api.constrains('journal_id', 'company_id')
    def _check_journal_company(self):
        for rec in self:
            if rec.journal_id and rec.journal_id.company_id != rec.company_id:
                raise ValidationError(_(
                    "The selected Journal '%(journal)s' belongs to %(journal_company)s, not to %(company)s.",
                    journal=rec.journal_id.name,
                    journal_company=rec.journal_id.company_id.name,
                    company=rec.company_id.name,
                ))

    @api.onchange('company_id')
    def _onchange_company_id(self):
        for rec in self:
            if rec.journal_id and rec.journal_id.company_id != rec.company_id:
                rec.journal_id = False

    @api.depends('name', 'code')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = '%s (%s)' % (rec.name, rec.code) if rec.code else rec.name


class SaleOrderBusiness(models.Model):
    _inherit = 'sale.order'

    business_model_id = fields.Many2one(
        'sale.business.model',
        string='Business Line',
        required=True,
        tracking=True,
        ondelete='restrict',
        copy=True,
    )

    @api.constrains('business_model_id', 'company_id')
    def _check_business_model_company(self):
        for order in self:
            model = order.business_model_id
            if model and model.company_id != order.company_id:
                raise ValidationError(_(
                    "The Business Model '%(model)s' belongs to %(company)s, not to the company of this order (%(order_company)s).",
                    model=model.name,
                    company=model.company_id.name,
                    order_company=order.company_id.name,
                ))

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        for order in orders:
            order._apply_business_prefix()
        return orders

    def write(self, vals):
        old_models = {}
        if 'business_model_id' in vals:
            old_models = {order.id: order.business_model_id for order in self}
        res = super().write(vals)
        if 'business_model_id' in vals:
            for order in self.filtered(lambda o: o.state in ('draft', 'sent')):
                order._apply_business_prefix(old_models.get(order.id))
        return res

    def _apply_business_prefix(self, old_model=None):
        """S00013 -> HP/S00013 (Short Code of the chosen Business Line)"""
        self.ensure_one()
        name = self.name or ''
        if not name or name == _("New"):
            return
        if old_model and old_model.code and name.startswith(old_model.code + '/'):
            name = name[len(old_model.code) + 1:]
        code = self.business_model_id.code
        if code and not name.startswith(code + '/'):
            name = '%s/%s' % (code, name)
        if name != self.name:
            self.name = name

    def _prepare_invoice(self):
        """Inapitisha Business Line na Journal yake kwenda kwenye Sale Invoice."""
        self.ensure_one()
        invoice_vals = super()._prepare_invoice()
        move_type = invoice_vals.get('move_type') or 'out_invoice'
        if move_type == 'out_invoice' and self.business_model_id:
            invoice_vals['business_model_id'] = self.business_model_id.id
            journal = self.business_model_id.journal_id
            if journal and journal.company_id == self.company_id:
                invoice_vals['journal_id'] = journal.id
        return invoice_vals

    def _create_invoices(self, grouped=False, final=False, date=None):
        """Safety net: inahakikisha draft customer invoice inapata Journal ya Business Line."""
        moves = super()._create_invoices(grouped=grouped, final=final, date=date)
        moves._apply_business_model_journal()
        return moves


class AccountMoveBusiness(models.Model):
    _inherit = 'account.move'

    business_model_id = fields.Many2one(
        'sale.business.model',
        string='Business Line',
        copy=False,
        index=True,
    )

    def _apply_business_model_journal(self):
        for move in self:
            journal = move.business_model_id.journal_id
            if (
                move.state == 'draft'
                and move.move_type == 'out_invoice'
                and journal
                and journal.company_id == move.company_id
                and move.journal_id != journal
            ):
                move.journal_id = journal

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        moves._apply_business_model_journal()
        return moves

    def write(self, vals):
        res = super().write(vals)
        if 'business_model_id' in vals and 'journal_id' not in vals:
            self._apply_business_model_journal()
        return res

    @api.onchange('business_model_id')
    def _onchange_business_model_id_journal(self):
        for move in self:
            if (
                move.is_sale_document(include_receipts=True)
                and move.business_model_id
                and move.business_model_id.journal_id
                and move.business_model_id.journal_id.company_id == move.company_id
            ):
                move.journal_id = move.business_model_id.journal_id