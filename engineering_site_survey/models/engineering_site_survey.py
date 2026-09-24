from odoo import api, fields, models, _
from odoo.exceptions import UserError
import datetime


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    survey_approver_id = fields.Many2one(
        'res.users',
        string='Default Site Survey Approver',
        config_parameter='engineering_site_survey.survey_approver_id',
        help='Select the default user who will approve site surveys.'
    )


class EngineeringExpenseType(models.Model):
    _name = 'engineering.expense.type'
    _description = 'Engineering Expense Type'
    _order = 'name'

    name = fields.Char(
        string='Expense Type Name',
        required=True
    )

    is_active = fields.Boolean(
        string='Active',
        default=True
    )


class EngineeringSiteSurveyProduct(models.Model):
    _name = 'engineering.site.survey.product'
    _description = 'Engineering Site Survey Product'
    _order = 'id'

    survey_id = fields.Many2one(
        'engineering.site.survey',
        required=True,
        ondelete='cascade'
    )

    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        tracking=True
    )

    description = fields.Char(
        string='Description'
    )

    currency_id = fields.Many2one(
        related='survey_id.currency_id',
        store=True,
        readonly=True
    )

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.description = self.product_id.name


class EngineeringSiteSurveyFuel(models.Model):
    _name = 'engineering.site.survey.fuel'
    _description = 'Engineering Site Survey Fuel Cost'
    _order = 'id'

    survey_id = fields.Many2one(
        'engineering.site.survey',
        required=True,
        ondelete='cascade'
    )

    vehicle_type = fields.Selection([
        ('individual', 'Individual'),
        ('company', 'Company Vehicle'),
    ],
        string='Vehicle Type',
        default='company',
        required=True,
        tracking=True
    )

    fuel_type = fields.Selection([
        ('diesel', 'Diesel'),
        ('petrol', 'Petrol'),
    ],
        string='Fuel Type',
        default='diesel',
        required=True,
        tracking=True
    )

    location_from = fields.Char(
        string='From',
        required=True
    )

    location_to = fields.Char(
        string='To',
        required=True
    )

    litres = fields.Float(
        string='Litres',
        default=0.0,
        required=True
    )

    price_per_litre = fields.Monetary(
        string='Price per Litre',
        currency_field='currency_id',
        default=0.0,
        required=True
    )

    total_amount = fields.Monetary(
        string='Total Fuel Cost',
        compute='_compute_total_amount',
        store=True,
        currency_field='currency_id'
    )

    currency_id = fields.Many2one(
        related='survey_id.currency_id',
        store=True,
        readonly=True
    )

    @api.depends('litres', 'price_per_litre')
    def _compute_total_amount(self):
        for line in self:
            line.total_amount = (
                line.litres *
                line.price_per_litre
            )


class EngineeringSiteSurvey(models.Model):
    _name = 'engineering.site.survey'
    _description = 'Engineering Site Survey'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    def _default_approver(self):
        approver_id = self.env['ir.config_parameter'].sudo().get_param(
            'engineering_site_survey.survey_approver_id'
        )

        return int(approver_id) if approver_id else False

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True
    )

    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        tracking=True
    )

    site_project = fields.Many2one(
        'project.project',
        string='Site / Project',
        tracking=True
    )

    location = fields.Char(
        string='Location',
        tracking=True
    )

    contact_person = fields.Char(
        string='Site Contact Person'
    )

    contact_phone = fields.Char(
        string='Contact Number'
    )

    responsible_engineer_id = fields.Many2one(
        'hr.employee',
        string='Responsible Engineer',
        tracking=True
    )

    approver_id = fields.Many2one(
        'res.users',
        string='Approver',
        default=_default_approver,
        tracking=True
    )

    is_approver = fields.Boolean(
        compute='_compute_is_approver'
    )

    is_responsible_engineer = fields.Boolean(
        compute='_compute_is_responsible_engineer'
    )

    def _compute_is_approver(self):
        approver_id = self.env['ir.config_parameter'].sudo().get_param(
            'engineering_site_survey.survey_approver_id'
        )

        current_user = self.env.user

        for rec in self:
            rec.is_approver = bool(
                approver_id
                and int(approver_id) == current_user.id
            )

    @api.depends('responsible_engineer_id')
    def _compute_is_responsible_engineer(self):
        current_user = self.env.user

        for rec in self:
            is_eng = False

            if rec.responsible_engineer_id:
                emp = rec.responsible_engineer_id

                if (
                    getattr(emp, 'user_id', False)
                    and emp.user_id == current_user
                ):
                    is_eng = True

                elif (
                    getattr(emp, 'work_email', False)
                    and emp.work_email
                    and current_user.email
                    and emp.work_email.lower() == current_user.email.lower()
                ):
                    is_eng = True

                elif (
                    emp.name
                    and current_user.name
                    and emp.name.strip().lower()
                    == current_user.name.strip().lower()
                ):
                    is_eng = True

                elif emp == current_user:
                    is_eng = True

                elif getattr(emp, 'id', None) == current_user.id:
                    is_eng = True

            if (
                current_user._is_admin()
                or current_user.has_group('base.group_system')
            ):
                is_eng = True

            rec.is_responsible_engineer = is_eng

    team_member_ids = fields.Many2many(
        'hr.employee',
        'engineering_survey_employee_rel',
        'survey_id',
        'employee_id',
        string='Team Members'
    )

    start_date = fields.Datetime(
        string='Planned Start',
        tracking=True
    )

    end_date = fields.Datetime(
        string='Planned End',
        tracking=True
    )

    due_date = fields.Datetime(
        string='Due Date',
        tracking=True
    )

    survey_purpose = fields.Html(
        string='Survey Purpose / Scope'
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('survey_done', 'Survey Done'),
        ('report_submitted', 'Report Submitted'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ],
        default='draft',
        string='Status',
        tracking=True,
        required=True
    )

    rejection_reason = fields.Text(
        string='Reason for Rejection',
        tracking=True
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.company.currency_id
    )

    expense_request_type = fields.Selection([
        ('individual', 'Individual'),
        ('group', 'Group'),
    ],
        string='Expense Request Type',
        default='individual',
        tracking=True,
        required=True
    )

    number_of_people = fields.Integer(
        string='Number of People',
        default=1,
        tracking=True
    )

    expense_line_ids = fields.One2many(
        'engineering.site.survey.expense',
        'survey_id',
        string='Expense Lines'
    )

    product_line_ids = fields.One2many(
        'engineering.site.survey.product',
        'survey_id',
        string='Product Lines'
    )

    fuel_line_ids = fields.One2many(
        'engineering.site.survey.fuel',
        'survey_id',
        string='Fuel Lines'
    )

    lead_ids = fields.One2many(
        'crm.lead',
        'survey_id',
        string='Leads'
    )

    lead_count = fields.Integer(
        compute='_compute_lead_count',
        string='Lead Count'
    )

    lead_created = fields.Boolean(
        string='Lead Created',
        default=False,
        copy=False
    )

    ticket_ids = fields.One2many(
        'helpdesk.ticket',
        'survey_id',
        string='Tickets'
    )

    ticket_count = fields.Integer(
        compute='_compute_ticket_count',
        string='Ticket Count'
    )

    ticket_created = fields.Boolean(
        string='Ticket Created',
        default=False,
        copy=False
    )

    @api.depends('lead_ids')
    def _compute_lead_count(self):
        for rec in self:
            rec.lead_count = len(rec.lead_ids)

    @api.depends('ticket_ids')
    def _compute_ticket_count(self):
        for rec in self:
            rec.ticket_count = len(rec.ticket_ids)

    expense_total = fields.Monetary(
        string='Expense Grand Total',
        compute='_compute_expense_total',
        currency_field='currency_id'
    )

    fuel_total = fields.Monetary(
        string='Fuel Grand Total',
        compute='_compute_fuel_total',
        store=True,
        currency_field='currency_id'
    )

    total_requested = fields.Monetary(
        string='Grand Total',
        compute='_compute_total_requested',
        store=True,
        currency_field='currency_id'
    )

    actual_survey_date = fields.Date(
        string='Actual Survey Date'
    )

    client_representative = fields.Char(
        string='Client Representative'
    )

    areas_inspected = fields.Html(
        string='Work / Areas Inspected'
    )

    site_conditions = fields.Html(
        string='Site Conditions'
    )

    technical_findings = fields.Html(
        string='Measurements / Technical Findings'
    )

    existing_infrastructure = fields.Html(
        string='Existing Equipment / Infrastructure'
    )

    issues_identified = fields.Html(
        string='Issues Identified'
    )

    client_requirements = fields.Html(
        string='Client Requirements'
    )

    engineer_observations = fields.Html(
        string='Engineer Observations'
    )

    recommendations = fields.Html(
        string='Recommendations'
    )

    proposed_solution = fields.Html(
        string='Proposed Solution / Scope of Work'
    )

    materials_required = fields.Html(
        string='Materials / Equipment Required'
    )

    safety_observations = fields.Html(
        string='Safety / Risk Observations'
    )

    additional_notes = fields.Html(
        string='Additional Notes'
    )

    conclusion = fields.Html(
        string='Conclusion'
    )

    @api.depends(
        'expense_line_ids',
        'expense_line_ids.amount'
    )
    def _compute_expense_total(self):
        for rec in self:
            rec.expense_total = sum(
                rec.expense_line_ids.mapped('amount')
            )

    @api.depends(
        'fuel_line_ids',
        'fuel_line_ids.total_amount'
    )
    def _compute_fuel_total(self):
        for rec in self:
            rec.fuel_total = sum(
                rec.fuel_line_ids.mapped('total_amount')
            )

    @api.depends(
        'expense_line_ids',
        'expense_line_ids.amount',
        'fuel_line_ids',
        'fuel_line_ids.total_amount'
    )
    def _compute_total_requested(self):
        for rec in self:
            total_expenses = sum(
                rec.expense_line_ids.mapped('amount')
            )

            total_fuel = sum(
                rec.fuel_line_ids.mapped('total_amount')
            )

            rec.total_requested = (
                total_expenses +
                total_fuel
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'engineering.site.survey'
                ) or _('New')

        return super().create(vals_list)

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for rec in self:
            if (
                rec.start_date
                and rec.end_date
                and rec.end_date < rec.start_date
            ):
                raise UserError(
                    _('Planned End must be after Planned Start.')
                )

    def action_submit(self):
        self.write({
            'state': 'submitted',
            'rejection_reason': False
        })

    def action_approve(self):
        approver_id = self.env['ir.config_parameter'].sudo().get_param(
            'engineering_site_survey.survey_approver_id'
        )

        if not approver_id or int(approver_id) != self.env.user.id:
            raise UserError(
                _('You are not authorized to approve this survey.')
            )

        self.write({
            'state': 'approved'
        })

    def action_cancel_approval(self):
        self.ensure_one()

        approver_id = self.env['ir.config_parameter'].sudo().get_param(
            'engineering_site_survey.survey_approver_id'
        )

        if not approver_id or int(approver_id) != self.env.user.id:
            raise UserError(
                _('You are not authorized to cancel this approval.')
            )

        self.write({
            'state': 'submitted'
        })

    def action_reject(self):
        approver_id = self.env['ir.config_parameter'].sudo().get_param(
            'engineering_site_survey.survey_approver_id'
        )

        if not approver_id or int(approver_id) != self.env.user.id:
            raise UserError(
                _('You are not authorized to reject this survey.')
            )

        return {
            'name': _('Reject Survey'),
            'type': 'ir.actions.act_window',
            'res_model': 'engineering.site.survey.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_survey_id': self.id
            },
        }

    def action_survey_done(self):
        self.write({
            'state': 'survey_done'
        })

    def action_submit_report(self):
        for rec in self:
            if not rec.actual_survey_date:
                raise UserError(
                    _(
                        'Please enter the Actual Survey Date '
                        'before submitting the report.'
                    )
                )

        self.write({
            'state': 'report_submitted'
        })

    def action_complete(self):
        self.write({
            'state': 'completed'
        })

    def action_cancel(self):
        self.write({
            'state': 'cancelled'
        })

    def action_reset_draft(self):
        self.write({
            'state': 'draft',
            'rejection_reason': False
        })

    def action_continue_lead(self):
        self.ensure_one()

        if 'crm.lead' not in self.env:
            raise UserError(
                _('CRM module is not installed or loaded.')
            )

        lead_vals = {
            'name': (
                f"Lead from Survey: "
                f"{self.name} - {self.partner_id.name}"
            ),
            'partner_id': self.partner_id.id,
            'contact_name': self.contact_person,
            'phone': self.contact_phone,
            'survey_id': self.id,
            'description': (
                f"<p>Generated from Engineering Site Survey: "
                f"<b>{self.name}</b></p>"
                f"<p>Location: {self.location or ''}</p>"
                f"<p>Proposed Solution: "
                f"{self.proposed_solution or ''}</p>"
            ),
        }

        self.env['crm.lead'].create(lead_vals)

        self.write({
            'lead_created': True
        })

        return {
            'effect': {
                'fadeout': 'slow',
                'message': _(
                    'Lead successfully created from Site Survey!'
                ),
                'type': 'rainbow_man',
            }
        }

    def action_reset_lead(self):
        self.ensure_one()

        if self.lead_ids:
            self.lead_ids.unlink()

        self.write({
            'lead_created': False
        })

        return {
            'effect': {
                'fadeout': 'slow',
                'message': _('Lead successfully reset!'),
                'type': 'rainbow_man',
            }
        }

    def action_help_desk(self):
        self.ensure_one()

        if 'helpdesk.ticket' not in self.env:
            raise UserError(
                _('Helpdesk module is not installed or loaded.')
            )

        ticket_vals = {
            'name': (
                f"Helpdesk Ticket from Survey: {self.name}"
            ),
            'partner_id': self.partner_id.id,
            'survey_id': self.id,
            'description': (
                f"<p>Created from Completed Site Survey: "
                f"<b>{self.name}</b></p>"
                f"<p>Issues Identified: "
                f"{self.issues_identified or ''}</p>"
                f"<p>Recommendations: "
                f"{self.recommendations or ''}</p>"
            ),
        }

        self.env['helpdesk.ticket'].create(ticket_vals)

        self.write({
            'ticket_created': True
        })

        return {
            'effect': {
                'fadeout': 'slow',
                'message': _(
                    'Helpdesk Ticket successfully created!'
                ),
                'type': 'rainbow_man',
            }
        }

    def action_reset_help_desk(self):
        self.ensure_one()

        if self.ticket_ids:
            self.ticket_ids.unlink()

        self.write({
            'ticket_created': False
        })

        return {
            'effect': {
                'fadeout': 'slow',
                'message': _('Helpdesk successfully reset!'),
                'type': 'rainbow_man',
            }
        }

    def action_view_leads(self):
        self.ensure_one()

        return {
            'name': _('Leads'),
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead',
            'view_mode': 'list,form',
            'domain': [
                ('survey_id', '=', self.id)
            ],
            'context': {
                'default_survey_id': self.id,
                'default_partner_id': self.partner_id.id
            },
        }

    def action_view_tickets(self):
        self.ensure_one()

        return {
            'name': _('Helpdesk Tickets'),
            'type': 'ir.actions.act_window',
            'res_model': 'helpdesk.ticket',
            'view_mode': 'list,form',
            'domain': [
                ('survey_id', '=', self.id)
            ],
            'context': {
                'default_survey_id': self.id,
                'default_partner_id': self.partner_id.id
            },
        }

    @api.model
    def get_engineering_dashboard_data(
        self,
        from_date=None,
        to_date=None,
        stage=None
    ):
        domain = []

        if from_date:
            domain.append(
                ('create_date', '>=', from_date)
            )

        if to_date:
            domain.append(
                ('create_date', '<=', to_date)
            )

        if stage and stage != 'all':
            domain.append(
                ('state', '=', stage)
            )

        surveys = self.search(domain)

        draft_count = len(
            surveys.filtered(
                lambda r: r.state == 'draft'
            )
        )

        pending_count = len(
            surveys.filtered(
                lambda r: r.state in (
                    'submitted',
                    'approved'
                )
            )
        )

        rejected_count = len(
            surveys.filtered(
                lambda r: r.state == 'rejected'
            )
        )

        verified_count = len(
            surveys.filtered(
                lambda r: r.state in (
                    'survey_done',
                    'report_submitted'
                )
            )
        )

        survey_done_count = len(
            surveys.filtered(
                lambda r: r.state == 'survey_done'
            )
        )

        report_submitted_count = len(
            surveys.filtered(
                lambda r: r.state == 'report_submitted'
            )
        )

        completed_count = len(
            surveys.filtered(
                lambda r: r.state == 'completed'
            )
        )

        total_count = len(surveys)

        total_amount = sum(
            surveys.mapped('total_requested')
        )

        lead_count = sum(
            surveys.mapped('lead_count')
        )

        ticket_count = sum(
            surveys.mapped('ticket_count')
        )

        engineer_data = []

        engineers = surveys.mapped(
            'responsible_engineer_id'
        )

        for engineer in engineers:
            engineer_data.append({
                'id': engineer.id,
                'name': engineer.name,
                'count': len(
                    surveys.filtered(
                        lambda r: (
                            r.responsible_engineer_id.id
                            == engineer.id
                        )
                    )
                ),
            })

        currencies = surveys.mapped('currency_id')

        if len(currencies) == 1:
            currency = currencies[0]
            currency_code = currency.name
            currency_symbol = (
                currency.symbol or currency.name
            )
        else:
            currency = self.env.company.currency_id
            currency_code = currency.name
            currency_symbol = (
                currency.symbol or currency.name
            )

        return {
            'draft_count': draft_count,
            'pending_count': pending_count,
            'rejected_count': rejected_count,
            'verified_count': verified_count,
            'survey_done_count': survey_done_count,
            'report_submitted_count': report_submitted_count,
            'completed_count': completed_count,
            'total_count': total_count,
            'total_amount': total_amount,
            'currency_code': currency_code,
            'currency_symbol': currency_symbol,
            'lead_count': lead_count,
            'ticket_count': ticket_count,
            'engineer_data': engineer_data,
        }


class EngineeringSiteSurveyExpense(models.Model):
    _name = 'engineering.site.survey.expense'
    _description = 'Engineering Site Survey Expense'
    _order = 'sequence, id'

    sequence = fields.Integer(
        default=10
    )

    survey_id = fields.Many2one(
        'engineering.site.survey',
        required=True,
        ondelete='cascade'
    )

    expense_type_id = fields.Many2one(
        'engineering.expense.type',
        string='Expense Type',
        required=True,
        domain="[('is_active', '=', True)]"
    )

    description = fields.Char(
        string='Description'
    )

    cost = fields.Monetary(
        string='Cost',
        required=True,
        currency_field='currency_id',
        default=0.0
    )

    amount = fields.Monetary(
        string='Amount',
        compute='_compute_amount',
        store=True,
        readonly=False,
        currency_field='currency_id'
    )

    currency_id = fields.Many2one(
        related='survey_id.currency_id',
        store=True,
        readonly=True
    )

    @api.depends(
        'cost',
        'survey_id.expense_request_type',
        'survey_id.number_of_people'
    )
    def _compute_amount(self):
        for line in self:
            if (
                line.survey_id.expense_request_type == 'group'
                and line.survey_id.number_of_people > 0
            ):
                line.amount = (
                    line.cost *
                    line.survey_id.number_of_people
                )
            else:
                line.amount = line.cost


class EngineeringSiteSurveyRejectWizard(models.TransientModel):
    _name = 'engineering.site.survey.reject.wizard'
    _description = 'Survey Rejection Wizard'

    survey_id = fields.Many2one(
        'engineering.site.survey',
        string='Survey',
        required=True
    )

    rejection_reason = fields.Text(
        string='Reason for Rejection',
        required=True
    )

    def action_confirm_rejection(self):
        self.ensure_one()

        self.survey_id.write({
            'state': 'rejected',
            'rejection_reason': self.rejection_reason
        })

        return {
            'type': 'ir.actions.act_window_close'
        }


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    survey_id = fields.Many2one(
        'engineering.site.survey',
        string='Site Survey',
        readonly=True
    )

    survey_count = fields.Integer(
        compute='_compute_survey_count',
        string='Survey Count'
    )

    @api.depends('survey_id')
    def _compute_survey_count(self):
        for lead in self:
            lead.survey_count = (
                1 if lead.survey_id else 0
            )

    def action_create_engineering_survey(self):
        self.ensure_one()

        if not self.partner_id:
            raise UserError(
                _(
                    'Please select a Customer on this Lead '
                    'before creating an Engineering Site Survey.'
                )
            )

        if not self.survey_id:
            survey_vals = {
                'partner_id': self.partner_id.id,
                'location': (
                    self.street
                    or self.city
                    or ''
                ),
                'contact_person': (
                    self.contact_name
                    or self.partner_id.name
                    or ''
                ),
                'contact_phone': (
                    self.phone
                    or self.mobile
                    or ''
                ),
                'state': 'draft',
            }

            new_survey = self.env[
                'engineering.site.survey'
            ].create(survey_vals)

            self.survey_id = new_survey.id

        return {
            'effect': {
                'fadeout': 'slow',
                'message': _(
                    'Engineering Site Survey successfully created '
                    'in Draft status!'
                ),
                'type': 'rainbow_man',
            }
        }

    def action_reset_engineering_survey(self):
        self.ensure_one()

        if self.survey_id:
            self.survey_id = False

        return {
            'effect': {
                'fadeout': 'slow',
                'message': _(
                    'Site Survey successfully reset!'
                ),
                'type': 'rainbow_man',
            }
        }


class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    survey_id = fields.Many2one(
        'engineering.site.survey',
        string='Site Survey',
        readonly=True
    )