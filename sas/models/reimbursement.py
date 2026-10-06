from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ClearanceReimbursement(models.Model):
    """
    Clearance Reimbursement Note – repays expenses incurred during customs clearing.
    Has its own sequence (RN.YY/MM/XXXXX) matching SAS Logistics naming convention.
    Prints with 'REIMBURSEMENT NOTE' heading matching the SAS Logistics template.
    """
    _name = 'clearance.reimbursement'
    _description = 'Clearance Reimbursement Note'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name desc'

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('clearance.reimbursement') or 'New'
        return super().create(vals)

    # ─────────────────────────────────────────
    # HEADER FIELDS
    # ─────────────────────────────────────────
    name = fields.Char(
        string='Reimbursement Reference', default='New',
        readonly=True, copy=False, tracking=True,
    )
    clearance_id = fields.Many2one(
        'clearance.record', string='Clearance Record',
        required=True, ondelete='restrict', tracking=True,
    )
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company, required=True,
    )
    partner_id = fields.Many2one(
        'res.partner', string='Customer / Recipient',
        required=True, tracking=True,
    )
    date = fields.Date(
        string='Reimbursement Date', default=fields.Date.today, required=True, tracking=True,
    )
    currency_id = fields.Many2one(
        'res.currency', related='clearance_id.currency_id', store=True,
    )

    # ─────────────────────────────────────────
    # REFERENCE DETAILS (printed on report)
    # ─────────────────────────────────────────
    shipping_route = fields.Char(
        string='Shipping Route',
        help="e.g. 'DSM - GEITA' – printed on the reimbursement note.",
    )
    payment_terms_note = fields.Char(
        string='Payment Terms',
        default='Within 62 days.',
        help="Printed under PAYMENT TERMS on the reimbursement note.",
    )
    sas_ref_no = fields.Char(
        string='SAS REF No',
        required=True,
        help="SAS reference number – printed on the reimbursement note.",
    )
    awb_no = fields.Char(
        string='AWB No',
        required=True,
        help="Air Waybill number – printed on the reimbursement note.",
    )
    po_no = fields.Char(
        string='PO No',
        required=True,
        help="Purchase Order number – printed on the reimbursement note.",
    )   


    # ─────────────────────────────────────────
    # LINES & TOTALS
    # ─────────────────────────────────────────
    line_ids = fields.One2many(
        'clearance.reimbursement.line', 'reimbursement_id', string='Expense Lines',
    )
    total_amount = fields.Monetary(
        string='Total Reimbursable', compute='_compute_total', store=True,
        currency_field='currency_id',
    )
    amount_in_words = fields.Char(
        string='Amount in Words', compute='_compute_amount_in_words', store=True,
        help="Auto-generated from total amount – printed on the reimbursement note.",
    )
    notes = fields.Text(string='Internal Notes')

    # ─────────────────────────────────────────
    # STATUS
    # ─────────────────────────────────────────
    state = fields.Selection([
        ('draft',     'Draft'),
        ('confirmed', 'Confirmed'),
        ('paid',      'Paid'),
        ('cancelled', 'Cancelled'),
    ], default='draft', tracking=True, copy=False, string='Status')

    # ─────────────────────────────────────────
    # COMPUTES
    # ─────────────────────────────────────────
    @api.depends('line_ids.amount')
    def _compute_total(self):
        for rec in self:
            rec.total_amount = sum(rec.line_ids.mapped('amount'))

    @api.depends('total_amount', 'currency_id')
    def _compute_amount_in_words(self):
        for rec in self:
            if rec.currency_id:
                rec.amount_in_words = rec.currency_id.amount_to_text(rec.total_amount)
            else:
                rec.amount_in_words = ''

    # ─────────────────────────────────────────
    # STATE ACTIONS
    # ─────────────────────────────────────────
    def action_confirm(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError(_("Add at least one expense line before confirming."))
            rec.state = 'confirmed'
            rec.message_post(body=_("Reimbursement confirmed. Total: %s %s") % (
                rec.currency_id.name, rec.total_amount
            ))

    def action_mark_paid(self):
        for rec in self:
            if rec.state != 'confirmed':
                raise UserError(_("Reimbursement must be confirmed before marking as paid."))
            rec.state = 'paid'
            rec.message_post(body=_("Reimbursement marked as paid."))

    def action_cancel(self):
        for rec in self:
            if rec.state == 'paid':
                raise UserError(_("Cannot cancel a paid reimbursement."))
            rec.state = 'cancelled'
            rec.message_post(body=_("Reimbursement cancelled."))

    def action_reset_draft(self):
        for rec in self:
            if rec.state == 'cancelled':
                rec.state = 'draft'



# ──────────────────────────────────────────────────────────────────
class ClearanceReimbursementLine(models.Model):
    """Individual expense line on a Clearance Reimbursement Note."""
    _name = 'clearance.reimbursement.line'
    _description = 'Reimbursement Line'
    _order = 'sequence, id'

    reimbursement_id = fields.Many2one(
        'clearance.reimbursement', string='Reimbursement', ondelete='cascade',
    )
    sequence = fields.Integer(default=10)
    expense_id = fields.Many2one('hr.expense', string='Source Expense', ondelete='set null')
    description = fields.Char(string='Description', required=True)
    employee_id = fields.Many2one('res.users', string='Incurred By')
    amount = fields.Monetary(string='Amount', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='reimbursement_id.currency_id', store=True)