from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class ClearanceRecord(models.Model):
    _name = 'clearance.record'
    _description = 'Clearance Record'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name desc, id desc'

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('clearance.record') or 'New'
        return super().create(vals)

    name = fields.Char(string='Reference', default='New', readonly=True, copy=False, tracking=True)
    shipping_order_id = fields.Many2one(
        'shipping.order', string='Shipping Order', required=True, ondelete='restrict', tracking=True,
    )
    handler = fields.Selection(
        [('our', 'SAS Logistics (In-House)'), ('other', 'Third-Party Agent')],
        string='Clearing Handler', required=True, tracking=True,
    )
    third_party_agent = fields.Char(string='Third-Party Agent Name')
    responsible_user_id = fields.Many2one(
        'res.users', string='Responsible Officer',
        default=lambda self: self.env.user, tracking=True,
    )
    clearance_date = fields.Date(string='Clearance Start Date', default=fields.Date.today)
    deadline = fields.Date(string='Clearing Deadline', required=True, tracking=True)
    state = fields.Selection([
        ('draft',       'Draft'),
        ('in_progress', 'In Progress'),
        ('done',        'Completed'),
        ('cancelled',   'Cancelled'),
    ], string='Status', default='draft', tracking=True, copy=False)

    currency_id = fields.Many2one('res.currency', related='shipping_order_id.currency_id')
    notes = fields.Html(string='General Notes')

    declaration_number = fields.Char(string='Declaration Number (TRA)', tracking=True)
    declaration_date = fields.Date(string='Declaration Date')
    pre_assessment_reviewed = fields.Boolean(string='Pre-Assessment Reviewed')
    pre_assessment_date = fields.Date(string='Pre-Assessment Date')
    final_assessment_date = fields.Date(string='Final Assessment Date')
    hs_code_clarified = fields.Boolean(string='HS Codes Clarified')

    # Government permits
    gcla_permit = fields.Boolean(string='GCLA Permit Required')
    gcla_permit_number = fields.Char(string='GCLA Permit No.')
    gcla_permit_date = fields.Date(string='GCLA Permit Date')

    tbs_permit = fields.Boolean(string='TBS Permit Required')
    tbs_permit_number = fields.Char(string='TBS Permit No.')
    tbs_permit_date = fields.Date(string='TBS Permit Date')

    tmda_permit = fields.Boolean(string='TMDA Permit Required')
    tmda_permit_number = fields.Char(string='TMDA Permit No.')
    tmda_permit_date = fields.Date(string='TMDA Permit Date')

    other_permit = fields.Boolean(string='Other Government Permit Required')
    other_permit_details = fields.Char(string='Other Permit Details')
    other_permit_number = fields.Char(string='Other Permit No.')

    bond_cancellation_required = fields.Boolean(string='Bond Cancellation Required')
    bond_cancellation_date = fields.Date(string='Bond Cancellation Date')
    bond_number = fields.Char(string='Bond Number')

    tra_query_notes = fields.Text(string='TRA / Government Query Notes')
    customs_officer = fields.Char(string='Customs Officer Name')

    # Duty & Tax
    duty_amount = fields.Monetary(string='Duty Amount', currency_field='currency_id')
    vat_amount = fields.Monetary(string='VAT Amount', currency_field='currency_id')
    excise_duty = fields.Monetary(string='Excise Duty', currency_field='currency_id')
    other_tax = fields.Monetary(string='Other Tax / Levy', currency_field='currency_id')
    total_duty_tax = fields.Monetary(
        string='Total Duty & Tax', compute='_compute_total_duty_tax', store=True,
        currency_field='currency_id',
    )

    bl_number = fields.Char(string='Bill of Lading No.')
    docs_submitted_to_shipping_line = fields.Boolean(string='Docs Submitted to Shipping Line')
    docs_submission_date = fields.Date(string='Docs Submission Date')

    shipping_line_invoice_received = fields.Boolean(string='Shipping Line Invoice Received')
    shipping_line_invoice_no = fields.Char(string='Shipping Line Invoice No.')
    shipping_line_invoice_amount = fields.Monetary(
        string='Shipping Line Invoice Amount', currency_field='currency_id',
    )
    shipping_line_paid = fields.Boolean(string='Shipping Line Invoice Paid')
    shipping_line_paid_date = fields.Date(string='Payment Date')

    do_received = fields.Boolean(string='Delivery Order (DO) Received', tracking=True)
    do_number = fields.Char(string='DO Number')
    do_date = fields.Date(string='DO Date')
    do_expiry_date = fields.Date(string='DO Expiry Date')

    # Container tracking
    container_line_ids = fields.One2many(
        'clearance.container.line', 'clearance_id', string='Containers',
    )

    deposit_required = fields.Boolean(string='Container Deposit Required')
    deposit_amount = fields.Monetary(string='Deposit Amount', currency_field='currency_id')
    deposit_paid_date = fields.Date(string='Deposit Paid Date')
    deposit_refunded = fields.Boolean(string='Deposit Refunded')
    deposit_refund_date = fields.Date(string='Deposit Refund Date')

    shipping_line_notes = fields.Text(string='Shipping Line Notes / Issues')

    docs_received_for_verification = fields.Boolean(string='Docs Received for Verification')
    docs_review_date = fields.Date(string='Docs Review Date')

    cargo_booked = fields.Boolean(string='Cargo Booked / Verified')
    cargo_booking_date = fields.Date(string='Cargo Booking Date')

    physical_verification_done = fields.Boolean(string='Physical Verification Done')
    physical_verification_date = fields.Date(string='Physical Verification Date')
    examination_type = fields.Selection([
        ('none', 'No Examination'),
        ('doc_check', 'Document Check Only'),
        ('scanner', 'Scanner Examination'),
        ('physical', 'Full Physical Examination'),
    ], string='Examination Type', default='none')

    port_charges_paid = fields.Boolean(string='Port / Airport Charges Paid')
    port_charges_amount = fields.Monetary(string='Port / Airport Charges', currency_field='currency_id')
    port_charges_paid_date = fields.Date(string='Port Charges Paid Date')

    gate_pass_prepared = fields.Boolean(string='Gate Pass Prepared', tracking=True)
    gate_pass_number = fields.Char(string='Gate Pass No.')
    gate_pass_date = fields.Date(string='Gate Pass Date')

    cargo_released = fields.Boolean(string='Cargo Released', tracking=True)
    cargo_release_date = fields.Date(string='Cargo Release Date')

    cargo_loaded = fields.Boolean(string='Cargo Loaded / Dispatched')
    cargo_loaded_date = fields.Date(string='Loaded Date')

    port_notes = fields.Text(string='Port / Airport Notes / Issues')

    other_fees = fields.Monetary(string='Other Clearing Fees', currency_field='currency_id')
    total_clearance_cost = fields.Monetary(
        string='Total Clearance Cost', compute='_compute_total_clearance_cost',
        store=True, currency_field='currency_id',
    )

    expense_ids = fields.One2many('hr.expense', 'clearance_record_id', string='Expenses')
    expense_count = fields.Integer(compute='_compute_expense_count', string='Expenses')
    total_expense_amount = fields.Float(
        string='Total Expense Amount', compute='_compute_total_expense_amount', store=True,
    )

    # New field for smart button visibility
    has_pending_expenses = fields.Boolean(
        string='Has Pending Expenses',
        compute='_compute_has_pending_expenses'
    )

    document_ids = fields.Many2many(
        'ir.attachment',
        'clearance_record_attachment_rel',
        'clearance_record_id',
        'attachment_id',
        string='Supporting Documents',
    )
    document_count = fields.Integer(compute='_compute_document_count', string='Documents')
    invoice_ids = fields.One2many(
        'account.move',
        'clearance_record_id',
        string='Invoices',
        domain=[('move_type', '=', 'out_invoice')]
    )
    invoice_count = fields.Integer(compute='_compute_invoice_count', string='Invoices')

    reimbursement_ids = fields.One2many(
        'account.move',
        'clearance_record_id',
        string='Reimbursements',
        domain=[('move_type', '=', 'in_refund')]
    )

    reimbursement_count = fields.Integer(
        string='Reimbursements',
        compute='_compute_reimbursement_count'
    )

    clearance_service_product_id = fields.Many2one(
        'product.product', string='Default Clearing Service Product',
        domain=[('type', '=', 'service')],
    )

    # ===================================================================
    # COMPUTED METHODS
    # ===================================================================

    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        for rec in self:
            rec.invoice_count = len(rec.invoice_ids)

    @api.depends('reimbursement_ids')
    def _compute_reimbursement_count(self):
        for rec in self:
            rec.reimbursement_count = len(rec.reimbursement_ids)

    

    @api.depends('duty_amount', 'vat_amount', 'excise_duty', 'other_tax')
    def _compute_total_duty_tax(self):
        for rec in self:
            rec.total_duty_tax = rec.duty_amount + rec.vat_amount + rec.excise_duty + rec.other_tax

    @api.depends('total_duty_tax', 'port_charges_amount', 'shipping_line_invoice_amount', 'other_fees')
    def _compute_total_clearance_cost(self):
        for rec in self:
            rec.total_clearance_cost = (
                rec.total_duty_tax
                + rec.port_charges_amount
                + rec.shipping_line_invoice_amount
                + rec.other_fees
            )

    @api.depends('expense_ids')
    def _compute_expense_count(self):
        for rec in self:
            rec.expense_count = len(rec.expense_ids)

    @api.depends('expense_ids.total_amount')
    def _compute_total_expense_amount(self):
        for rec in self:
            rec.total_expense_amount = sum(rec.expense_ids.mapped('total_amount'))

    @api.depends('document_ids')
    def _compute_document_count(self):
        for rec in self:
            rec.document_count = len(rec.document_ids)

    @api.depends('expense_ids', 'reimbursement_ids')
    def _compute_has_pending_expenses(self):
        """Show Create Reimbursement button only if there are expenses"""
        for rec in self:
            rec.has_pending_expenses = bool(rec.expense_ids)

    # ===================================================================
    # BUSINESS METHODS
    # ===================================================================

    def _create_container_lines_from_shipping(self, clearance):
        """Create clearance.container.line records from shipping.order.line"""
        ShippingLine = self.env['shipping.order.line']
        shipping_lines = ShippingLine.search([
            ('order_id', '=', clearance.shipping_order_id.id),
            ('container_number', '!=', False),
            ('container_number', '!=', '')
        ])

        container_lines_to_create = []
        existing_containers = clearance.container_line_ids.mapped('container_number')

        for line in shipping_lines:
            if line.container_number in existing_containers:
                continue
            container_lines_to_create.append({
                'clearance_id': clearance.id,
                'container_number': line.container_number,
                'seal_number': line.seal_number,
                'container_size': self._guess_container_size(line.container_number),
            })

        if container_lines_to_create:
            self.env['clearance.container.line'].create(container_lines_to_create)
            clearance.message_post(
                body=_("Automatically created %s container line(s) from Shipping Order.") 
                     % len(container_lines_to_create)
            )

    def _guess_container_size(self, container_number):
        if not container_number:
            return '20gp'
        cn = container_number.upper()
        if '40' in cn:
            return '40hc' if 'HC' in cn else '40gp'
        elif '20' in cn:
            return '20gp'
        return '20gp'

    def action_create_reimbursement(self):
        """Open wizard to select which expenses to reimburse"""
        self.ensure_one()

        if self.state != 'done':
            raise UserError(_("Clearance must be completed before creating a reimbursement."))

        if not self.expense_ids:
            raise UserError(_("There are no expenses available for reimbursement."))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Select Expenses for Reimbursement'),
            'res_model': 'clearance.reimbursement.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_clearance_id': self.id,
            },
        }

    def action_create_invoice(self):
        self.ensure_one()
        if self.state != 'done':
            raise UserError(_("Clearance must be completed before creating an invoice."))

        product = self.clearance_service_product_id or self.env['ir.config_parameter'].sudo().get_param('clearance.default_service_product')
        product_rec = self.env['product.product'].browse(int(product) if isinstance(product, str) else product)

        invoice_line_vals = [(0, 0, {
            'product_id': product_rec.id if product_rec else False,
            'name': _("Customs Clearing Service – %s") % self.name,
            'quantity': 1,
            'price_unit': self.total_clearance_cost,
        })]

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.shipping_order_id.consignee_id.id,
            'invoice_date': fields.Date.today(),
            'invoice_origin': self.name,
            'clearance_record_id': self.id,
            'invoice_line_ids': invoice_line_vals,
            'ref': self.shipping_order_id.client_po_number or '',
            'narration': _("Invoice for customs clearing: %s") % self.name,
        })

        self.message_post(body=_("Invoice %s created.") % invoice.name)

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': invoice.id,
            'target': 'current',
        }

    def action_start(self):
        for rec in self:
            rec.write({'state': 'in_progress'})
            rec.message_post(body=_("Clearance process started."))

    def action_complete(self):
        for rec in self:
            if rec.state != 'in_progress':
                raise UserError(_("Clearance must be In Progress to complete."))
            rec.write({'state': 'done'})
            rec.message_post(body=_("Clearance completed."))
            rec.shipping_order_id.action_cleared()

    def action_cancel(self):
        for rec in self:
            if rec.state == 'done':
                raise UserError(_("Cannot cancel a completed clearance record."))
            rec.write({'state': 'cancelled'})
            rec.message_post(body=_("Clearance record cancelled."))

    # View actions
    def action_view_expenses(self):
        self.ensure_one()
        return {
            'name': _('Clearing Expenses'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.expense',
            'view_mode': 'list,form',
            'domain': [('clearance_record_id', '=', self.id)],
            'context': {'default_clearance_record_id': self.id},
        }


    def action_view_reimbursements(self):
        self.ensure_one()

        action = {
            'name': _('Reimbursements'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [
                ('clearance_record_id', '=', self.id),
                ('move_type', '=', 'in_refund')
            ],
            'context': {
                'default_clearance_record_id': self.id,
                'default_move_type': 'in_refund',
            }
        }

        if self.reimbursement_count == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.reimbursement_ids.id,
            })

        return action

    def action_view_invoices(self):
        self.ensure_one()
        action = {
            'name': _('Invoices'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('clearance_record_id', '=', self.id), ('move_type', '=', 'out_invoice')],
            'context': {
                'default_clearance_record_id': self.id,
                'default_move_type': 'out_invoice',
            }
        }
        if self.invoice_count == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.invoice_ids.id,
            })
        return action


# ===================================================================
# CONTAINER LINE
# ===================================================================
class ClearanceContainerLine(models.Model):
    _name = 'clearance.container.line'
    _description = 'Clearance Container Line'

    clearance_id = fields.Many2one('clearance.record', string='Clearance Record', ondelete='cascade')
    container_number = fields.Char(string='Container No.', required=True)
    container_size = fields.Selection([
        ('20gp', "20' GP"), ('40gp', "40' GP"), ('40hc', "40' HC"),
        ('20rf', "20' Reefer"), ('40rf', "40' Reefer"), ('other', 'Other'),
    ], string='Size', default='20gp')
    seal_number = fields.Char(string='Seal No.')
    empty_returned = fields.Boolean(string='Empty Returned')
    empty_return_date = fields.Date(string='Return Date')
    return_notes = fields.Char(string='Return Notes')


# ===================================================================
# REIMBURSEMENT WIZARD (Improved)
# ===================================================================
class ClearanceReimbursementWizard(models.TransientModel):
    _name = 'clearance.reimbursement.wizard'
    _description = 'Clearance Reimbursement Selection Wizard'

    clearance_id = fields.Many2one('clearance.record', string='Clearance Record', required=True)
    
    expense_line_ids = fields.Many2many(
        'hr.expense',
        string='Select Expenses for Reimbursement',
        domain="[('clearance_record_id', '=', clearance_id)]",  # Removed strict state filter
        required=True,
    )

    @api.onchange('clearance_id')
    def _onchange_clearance_id(self):
        """Auto-fill all available expenses when wizard opens"""
        if self.clearance_id:
            expenses = self.env['hr.expense'].search([
                ('clearance_record_id', '=', self.clearance_id.id),
                ('state', 'in', ['done', 'approved'])  # You can adjust states
            ])
            self.expense_line_ids = expenses

    def action_create_reimbursement(self):
        self.ensure_one()

        if not self.expense_line_ids:
            raise UserError(_("Please select at least one expense."))

        partner = self.clearance_id.shipping_order_id.consignee_id
        if not partner:
            raise UserError(_("Please configure a consignee/customer on the Shipping Order."))

        invoice_lines = []
        for exp in self.expense_line_ids:
            line_vals = {
                'name': exp.name or _('Expense Reimbursement'),
                'quantity': 1,
                'price_unit': exp.total_amount or 0.0,
            }
            if exp.product_id:
                line_vals['product_id'] = exp.product_id.id
            if exp.tax_ids:
                line_vals['tax_ids'] = [(6, 0, exp.tax_ids.ids)]

            invoice_lines.append((0, 0, line_vals))

        reimbursement = self.env['account.move'].create({
            'move_type': 'in_refund',
            'partner_id': partner.id,
            'invoice_date': fields.Date.today(),
            'clearance_record_id': self.clearance_id.id,
            'invoice_origin': self.clearance_id.shipping_order_id.name,
            'sas_ref_no': self.clearance_id.shipping_order_id.name,
            'awb_no': self.clearance_id.shipping_order_id.pad_number,
            'po_no': self.clearance_id.shipping_order_id.client_po_number,
            'ref': _('Clearance Reimbursement - %s') % self.clearance_id.shipping_order_id.name,
            'invoice_line_ids': invoice_lines,
        })


        self.clearance_id.message_post(
            body=_("Reimbursement %s created for %s expense(s).") % 
                 (reimbursement.name, len(self.expense_line_ids))
        )

        return {
            'type': 'ir.actions.act_window',
            'name': _('Reimbursement'),
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': reimbursement.id,
            'target': 'current',
        }


# ===================================================================
# WIZARD & INHERITED MODELS
# ===================================================================
class ClearingWizard(models.TransientModel):
    _name = 'clearing.wizard'
    _description = 'Start Clearing Wizard'

    shipping_order_id = fields.Many2one('shipping.order', string='Shipping Order', required=True)
    handler = fields.Selection(
        [('our', 'SAS Logistics (In-House)'), ('other', 'Third-Party Agent')],
        string='Clearing Handler', required=True,
    )
    third_party_agent = fields.Char(string='Third-Party Agent Name')
    deadline = fields.Date(string='Clearing Deadline', required=True)

    def action_confirm_clearing(self):
        self.ensure_one()
        clearance = self.env['clearance.record'].create({
            'shipping_order_id': self.shipping_order_id.id,
            'handler': self.handler,
            'third_party_agent': self.third_party_agent or '',
            'deadline': self.deadline,
            'state': 'in_progress',
        })

        clearance._create_container_lines_from_shipping(clearance)

        self.shipping_order_id.write({'state': 'clearing'})

        clearance.activity_schedule(
            'mail.mail_activity_data_deadline',
            summary=_('Clearing Deadline Approaching'),
            note=_('Please ensure clearance is completed before the deadline.'),
            date_deadline=self.deadline,
            user_id=clearance.responsible_user_id.id or self.env.user.id,
        )

        self.shipping_order_id.message_post(
            body=_("Clearing process started. Clearance Record: %s") % clearance.name
        )

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'clearance.record',
            'view_mode': 'form',
            'res_id': clearance.id,
            'target': 'current',
        }


class HrExpense(models.Model):
    _inherit = 'hr.expense'
    clearance_record_id = fields.Many2one('clearance.record', string='Clearance Record', index=True)
    control_number = fields.Char(string='Control No.')


class AccountMove(models.Model):
    _inherit = 'account.move'

    clearance_record_id = fields.Many2one('clearance.record', string='Clearance Record', index=True)
    sas_ref_no = fields.Char(string='SAS REF No')
    awb_no = fields.Char(string='AWB No')
    po_no = fields.Char(string='PO No')
    route_name = fields.Char(string='Route Name')
    terms_template_id = fields.Many2one(
        'sale.terms.template', 
        string='Override Terms Template'
    )

    @api.onchange('terms_template_id')
    def _onchange_terms_template_id(self):
        """Replaces the default terms with the selected template's content"""
        if self.terms_template_id:
            self.narration = self.terms_template_id.note

    def action_print_reimbursement(self):
        self.ensure_one()
        return self.env.ref('sas.action_report_reimbursement_note').report_action(self)