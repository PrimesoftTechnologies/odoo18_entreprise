from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, Command
from odoo.exceptions import UserError, ValidationError


class Asset(models.Model):
    _name = 'asset.asset'
    _description = 'Asset'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _mail_post_access = 'read'
    _order = 'code desc, id desc'

    # ---------------------------------------------------------------- General
    name = fields.Char('Asset Name', required=True, tracking=True)
    code = fields.Char('Asset Number', default='New', copy=False, readonly=True,
                       index=True, tracking=True)
    barcode = fields.Char('Barcode / QR Value', copy=False, index=True)
    active = fields.Boolean(default=True)
    image_1920 = fields.Image('Photo')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('available', 'Available'),
        ('in_use', 'In Use'),
        ('maintenance', 'Under Maintenance'),
        ('disposed', 'Disposed'),
    ], default='draft', tracking=True, copy=False, required=True)
    category_id = fields.Many2one('asset.category', string='Category', required=True,
                                  tracking=True, index=True)
    serial_no = fields.Char('Serial Number', copy=False)
    model_no = fields.Char('Model')
    brand = fields.Char()
    notes = fields.Html()
    company_id = fields.Many2one('res.company', required=True, index=True,
                                 default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id', store=True)

    # --------------------------------------------------------------- Custody
    employee_id = fields.Many2one('hr.employee', string='Current Holder', readonly=True,
                                  tracking=True, copy=False)
    department_id = fields.Many2one('hr.department', string='Department', tracking=True)
    location_id = fields.Many2one('asset.location', string='Location', tracking=True,
                                  domain="[('company_id', '=', company_id)]")
    responsible_id = fields.Many2one('res.users', string='Asset Manager / Custodian',
                                     default=lambda self: self.env.user)

    # ----------------------------------------------------------- Acquisition
    purchase_date = fields.Date(default=fields.Date.context_today, tracking=True)
    vendor_id = fields.Many2one('res.partner', string='Vendor')
    invoice_id = fields.Many2one('account.move', string='Vendor Bill',
                                 domain="[('move_type', '=', 'in_invoice')]", copy=False)
    purchase_value = fields.Monetary('Purchase Value', currency_field='currency_id', tracking=True)
    warranty_start = fields.Date()
    warranty_end = fields.Date('Warranty Expiry', tracking=True)
    insurance_provider = fields.Char()
    insurance_policy = fields.Char('Policy Number')
    insurance_expiry = fields.Date('Insurance Expiry')

    # ---------------------------------------------------------- Depreciation
    method = fields.Selection([
        ('linear', 'Straight-Line'),
        ('degressive', 'Declining Balance'),
        ('manual', 'Manual / No Depreciation'),
    ], compute='_compute_from_category', store=True, readonly=False, precompute=True,
        string='Method')
    useful_life = fields.Integer('Useful Life (Months)', compute='_compute_from_category',
                                 store=True, readonly=False, precompute=True)
    degressive_factor = fields.Float('Declining Factor', compute='_compute_from_category',
                                     store=True, readonly=False, precompute=True)
    salvage_value = fields.Monetary(compute='_compute_salvage_value', store=True,
                                    readonly=False, currency_field='currency_id')
    depreciable_value = fields.Monetary(compute='_compute_depreciable_value', store=True,
                                        currency_field='currency_id')
    first_depreciation_date = fields.Date(compute='_compute_first_depreciation_date',
                                          store=True, readonly=False)
    depreciation_line_ids = fields.One2many('asset.depreciation.line', 'asset_id',
                                            string='Depreciation Schedule', copy=False)
    depreciated_value = fields.Monetary('Accumulated Depreciation',
                                        compute='_compute_values', store=True,
                                        currency_field='currency_id')
    book_value = fields.Monetary('Net Book Value', compute='_compute_values', store=True,
                                 currency_field='currency_id')

    # ------------------------------------------------------------- Relations
    assignment_ids = fields.One2many('asset.assignment', 'asset_id', string='Assignments')
    maintenance_ids = fields.One2many('asset.maintenance', 'asset_id', string='Maintenance')
    assignment_count = fields.Integer(compute='_compute_counts')
    maintenance_count = fields.Integer(compute='_compute_counts')
    transfer_count = fields.Integer(compute='_compute_counts')

    _sql_constraints = [
        ('code_company_uniq', 'unique(code, company_id)', 'The asset number must be unique per company!'),
    ]

    # ------------------------------------------------------------- Computes
    @api.depends('category_id')
    def _compute_from_category(self):
        for asset in self:
            cat = asset.category_id
            if cat:
                asset.method = cat.method
                asset.useful_life = cat.useful_life
                asset.degressive_factor = cat.degressive_factor
            else:
                asset.method = asset.method or 'linear'
                asset.useful_life = asset.useful_life or 0
                asset.degressive_factor = asset.degressive_factor or 0.0

    @api.depends('category_id', 'purchase_value')
    def _compute_salvage_value(self):
        for asset in self:
            asset.salvage_value = asset.purchase_value * (asset.category_id.salvage_percent / 100.0)

    @api.depends('purchase_value', 'salvage_value')
    def _compute_depreciable_value(self):
        for asset in self:
            asset.depreciable_value = asset.purchase_value - asset.salvage_value

    @api.depends('purchase_date')
    def _compute_first_depreciation_date(self):
        for asset in self:
            asset.first_depreciation_date = (
                fields.Date.end_of(asset.purchase_date, 'month') if asset.purchase_date else False)

    @api.depends('purchase_value', 'depreciation_line_ids.amount', 'depreciation_line_ids.state')
    def _compute_values(self):
        for asset in self:
            posted = asset.depreciation_line_ids.filtered(lambda l: l.state == 'posted')
            asset.depreciated_value = sum(posted.mapped('amount'))
            asset.book_value = asset.purchase_value - asset.depreciated_value

    def _compute_counts(self):
        for asset in self:
            asset.assignment_count = self.env['asset.assignment'].search_count(
                [('asset_id', '=', asset.id)])
            asset.maintenance_count = self.env['asset.maintenance'].search_count(
                [('asset_id', '=', asset.id)])
            asset.transfer_count = self.env['asset.transfer'].search_count(
                [('asset_id', '=', asset.id)])

    # ---------------------------------------------------------- Constraints
    @api.constrains('purchase_value', 'salvage_value', 'useful_life')
    def _check_values(self):
        for asset in self:
            if asset.purchase_value < 0 or asset.salvage_value < 0:
                raise ValidationError(self.env._("Values cannot be negative."))
            if asset.salvage_value > asset.purchase_value:
                raise ValidationError(self.env._("Salvage value cannot exceed the purchase value."))
            if asset.useful_life < 0:
                raise ValidationError(self.env._("Useful life cannot be negative."))

    @api.constrains('warranty_start', 'warranty_end')
    def _check_warranty(self):
        for asset in self:
            if asset.warranty_start and asset.warranty_end and asset.warranty_end < asset.warranty_start:
                raise ValidationError(self.env._("Warranty expiry cannot be before its start."))

    # -------------------------------------------------------------- ORM
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('code', 'New') == 'New':
                vals['code'] = self.env['ir.sequence'].next_by_code('asset.asset') or 'New'
            if not vals.get('barcode'):
                vals['barcode'] = vals['code']
        return super().create(vals_list)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_in_progress(self):
        for asset in self:
            if asset.state != 'draft':
                raise UserError(self.env._(
                    "Only draft assets can be deleted. Dispose or archive asset %s instead.", asset.display_name))

    def copy_data(self, default=None):
        default = dict(default or {})
        default.setdefault('serial_no', False)
        return super().copy_data(default)

    @api.onchange('invoice_id')
    def _onchange_invoice_id(self):
        inv = self.invoice_id
        if inv:
            self.vendor_id = inv.partner_id
            self.purchase_date = inv.invoice_date or self.purchase_date
            self.purchase_value = inv.amount_untaxed

    def _compute_display_name(self):
        for asset in self:
            asset.display_name = '[%s] %s' % (asset.code, asset.name) if asset.code else asset.name

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        domain = list(domain or [])
        if name:
            domain = ['|', '|', '|', ('name', operator, name), ('code', operator, name),
                      ('barcode', operator, name), ('serial_no', operator, name)] + domain
        return self._search(domain, limit=limit, order=order)

    # ------------------------------------------------------- Workflow actions
    def action_confirm(self):
        for asset in self:
            if asset.state != 'draft':
                continue
            if asset.purchase_value <= 0 and asset.method != 'manual':
                raise UserError(self.env._("Set a purchase value on %s before confirming.", asset.display_name))
            asset.state = 'available'
            asset.compute_depreciation_board()
            asset.message_post(body=self.env._("Asset confirmed and available."))

    def action_set_draft(self):
        for asset in self:
            if asset.depreciation_line_ids.filtered(lambda l: l.state == 'posted'):
                raise UserError(self.env._("Cannot reset to draft: depreciation entries are already posted."))
            asset.depreciation_line_ids.unlink()
            asset.state = 'draft'

    def action_set_available_from_maint(self):
        """Used by maintenance when work is finished."""
        for asset in self:
            if asset.state == 'maintenance':
                asset.state = 'in_use' if asset.employee_id else 'available'

    # ---------------------------------------------------------- Depreciation
    def compute_depreciation_board(self):
        Line = self.env['asset.depreciation.line']
        for asset in self:
            Line.search([('asset_id', '=', asset.id), ('state', '=', 'draft')]).unlink()
            if (asset.method == 'manual' or asset.useful_life <= 0
                    or asset.depreciable_value <= 0 or not asset.first_depreciation_date):
                continue
            posted = Line.search([('asset_id', '=', asset.id), ('state', '=', 'posted')],
                                 order='sequence')
            done = sum(posted.mapped('amount'))
            remaining = asset.depreciable_value - done
            periods = asset.useful_life - len(posted)
            if remaining <= 0 or periods <= 0:
                continue
            if posted:
                start = fields.Date.end_of(posted[-1].date + relativedelta(months=1), 'month')
                seq = posted[-1].sequence
            else:
                start = asset.first_depreciation_date
                seq = 0
            book = asset.purchase_value - done
            vals_list = []
            for i in range(periods):
                left = periods - i
                if left == 1:
                    amount = remaining
                else:
                    amount = remaining / left
                    if asset.method == 'degressive':
                        amount = max(book * asset.degressive_factor / 12.0, amount)
                    amount = min(asset.currency_id.round(amount), remaining)
                if amount <= 0:
                    break
                seq += 1
                vals_list.append({
                    'asset_id': asset.id,
                    'sequence': seq,
                    'date': fields.Date.end_of(start + relativedelta(months=i), 'month'),
                    'amount': amount,
                })
                remaining -= amount
                book -= amount
            Line.create(vals_list)

    # ------------------------------------------------------- Opening helpers
    def _open_form(self, model, name, ctx=None):
        self.ensure_one()
        context = {'default_asset_id': self.id}
        context.update(ctx or {})
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': model,
            'view_mode': 'form',
            'target': 'current',
            'context': context,
        }

    def action_assign(self):
        return self._open_form('asset.assignment', self.env._('Assign Asset'),
                               {'default_location_id': self.location_id.id})

    def action_transfer(self):
        return self._open_form('asset.transfer', self.env._('Transfer Asset'))

    def action_request_maintenance(self):
        return self._open_form('asset.maintenance', self.env._('Maintenance Request'))

    def action_dispose(self):
        return self._open_form('asset.disposal', self.env._('Dispose Asset'))

    def _view_related(self, model, name):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': model,
            'view_mode': 'list,form',
            'domain': [('asset_id', '=', self.id)],
            'context': {'default_asset_id': self.id},
        }

    def action_view_assignments(self):
        return self._view_related('asset.assignment', self.env._('Assignments'))

    def action_view_maintenance(self):
        return self._view_related('asset.maintenance', self.env._('Maintenance'))

    def action_view_transfers(self):
        return self._view_related('asset.transfer', self.env._('Transfers'))

    def action_print_tag(self):
        return self.env.ref('asset_management_prime.action_report_asset_tag').report_action(self)

    # --------------------------------------------------------------- Cron
    @api.model
    def _schedule_alert(self, asset, summary, deadline):
        if not deadline:
            return
        existing = asset.activity_ids.filtered(lambda a: a.summary == summary)
        if existing:
            return
        user = asset.responsible_id or self.env.ref('base.user_admin')
        asset.activity_schedule(
            'mail.mail_activity_data_todo', date_deadline=deadline,
            summary=summary, user_id=user.id)

    @api.model
    def _cron_asset_alerts(self, days_before=30):
        today = fields.Date.context_today(self)
        limit = today + relativedelta(days=days_before)
        active_states = ['available', 'in_use', 'maintenance']

        # Warranty expiring
        for asset in self.search([('state', 'in', active_states), ('warranty_end', '!=', False),
                                  ('warranty_end', '<=', limit), ('warranty_end', '>=', today)]):
            self._schedule_alert(asset, self.env._("Warranty expiring"), asset.warranty_end)
        # Insurance expiring
        for asset in self.search([('state', 'in', active_states), ('insurance_expiry', '!=', False),
                                  ('insurance_expiry', '<=', limit), ('insurance_expiry', '>=', today)]):
            self._schedule_alert(asset, self.env._("Insurance expiring"), asset.insurance_expiry)
        # Preventive maintenance due
        maints = self.env['asset.maintenance'].search([
            ('state', '=', 'new'), ('maintenance_type', '=', 'preventive'),
            ('scheduled_date', '!=', False), ('scheduled_date', '<=', limit)])
        for m in maints:
            self._schedule_alert(m.asset_id, self.env._("Preventive maintenance due"), m.scheduled_date)
        # Overdue loans
        loans = self.env['asset.assignment'].search([
            ('state', '=', 'active'), ('expected_return_date', '!=', False),
            ('expected_return_date', '<', today)])
        for loan in loans:
            self._schedule_alert(loan.asset_id, self.env._("Asset return overdue"),
                                 loan.expected_return_date)
