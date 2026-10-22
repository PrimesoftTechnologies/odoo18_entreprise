from odoo import api, fields, models
from odoo.exceptions import UserError


class AssetAudit(models.Model):
    _name = 'asset.audit'
    _description = 'Asset Audit / Physical Verification'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char('Reference', default='New', copy=False, readonly=True)
    title = fields.Char('Audit Title', required=True, tracking=True)
    date = fields.Date(default=fields.Date.context_today, required=True)
    company_id = fields.Many2one('res.company', required=True,
                                 default=lambda self: self.env.company)
    auditor_id = fields.Many2one('res.users', string='Auditor', default=lambda self: self.env.user,
                                 tracking=True)
    scope = fields.Selection([
        ('all', 'All Assets'), ('location', 'By Location'),
        ('department', 'By Department'), ('category', 'By Category')],
        default='all', required=True)
    location_id = fields.Many2one('asset.location', string='Location')
    department_id = fields.Many2one('hr.department', string='Department')
    category_id = fields.Many2one('asset.category', string='Category')
    scan_location_id = fields.Many2one(
        'asset.location', string='Current Scan Location',
        help="Location where you are physically scanning. Assets found elsewhere are flagged as misplaced.")
    scan_input = fields.Char('Scan Barcode', store=False)
    line_ids = fields.One2many('asset.audit.line', 'audit_id', string='Audit Lines')
    state = fields.Selection([
        ('draft', 'Draft'), ('in_progress', 'In Progress'),
        ('done', 'Completed'), ('cancel', 'Cancelled')],
        default='draft', tracking=True, copy=False, required=True)

    total_count = fields.Integer(compute='_compute_counts')
    found_count = fields.Integer(compute='_compute_counts')
    missing_count = fields.Integer(compute='_compute_counts')
    misplaced_count = fields.Integer(compute='_compute_counts')
    pending_count = fields.Integer(compute='_compute_counts')

    @api.depends('line_ids.status')
    def _compute_counts(self):
        for rec in self:
            st = rec.line_ids.mapped('status')
            rec.total_count = len(st)
            rec.found_count = st.count('found')
            rec.missing_count = st.count('missing')
            rec.misplaced_count = st.count('misplaced')
            rec.pending_count = st.count('pending')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('asset.audit') or 'New'
        return super().create(vals_list)

    def _scope_domain(self):
        self.ensure_one()
        domain = [('state', 'in', ('available', 'in_use', 'maintenance')),
                  ('company_id', '=', self.company_id.id)]
        if self.scope == 'location' and self.location_id:
            domain.append(('location_id', 'child_of', self.location_id.id))
        elif self.scope == 'department' and self.department_id:
            domain.append(('department_id', '=', self.department_id.id))
        elif self.scope == 'category' and self.category_id:
            domain.append(('category_id', '=', self.category_id.id))
        return domain

    def action_start(self):
        for rec in self:
            assets = self.env['asset.asset'].search(rec._scope_domain())
            if not assets:
                raise UserError(self.env._("No assets match the selected scope."))
            self.env['asset.audit.line'].create([{
                'audit_id': rec.id,
                'asset_id': a.id,
                'expected_location_id': a.location_id.id,
                'expected_holder_id': a.employee_id.id,
            } for a in assets])
            rec.state = 'in_progress'

    def action_done(self):
        for rec in self:
            rec.line_ids.filtered(lambda l: l.status == 'pending').write({'status': 'missing'})
            rec.state = 'done'

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_set_draft(self):
        for rec in self:
            rec.line_ids.unlink()
            rec.state = 'draft'

    def action_apply_corrections(self):
        """Update the asset location for misplaced assets (manager only)."""
        if not self.env.user.has_group('asset_management_prime.group_asset_manager'):
            raise UserError(self.env._("Only an Asset Manager can apply audit corrections."))
        for rec in self:
            for line in rec.line_ids.filtered(lambda l: l.status == 'misplaced' and not l.applied):
                line.asset_id.location_id = line.found_location_id
                line.applied = True
                line.asset_id.message_post(body=self.env._(
                    "Location corrected by audit %s.", rec.name))

    @api.onchange('scan_input')
    def _onchange_scan_input(self):
        code = (self.scan_input or '').strip()
        if not code or self.state != 'in_progress':
            return
        line = self.line_ids.filtered(
            lambda l: code in (l.asset_id.barcode, l.asset_id.code, l.asset_id.serial_no))[:1]
        self.scan_input = False
        if not line:
            return {'warning': {
                'title': self.env._("Unknown asset"),
                'message': self.env._("'%s' is not part of this audit (unrecorded asset or outside scope).", code)}}
        line._mark_found(self.scan_location_id)


class AssetAuditLine(models.Model):
    _name = 'asset.audit.line'
    _description = 'Asset Audit Line'
    _order = 'status, id'

    audit_id = fields.Many2one('asset.audit', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one(related='audit_id.company_id', store=True)
    asset_id = fields.Many2one('asset.asset', required=True)
    category_id = fields.Many2one(related='asset_id.category_id', store=True)
    expected_location_id = fields.Many2one('asset.location', string='Expected Location')
    expected_holder_id = fields.Many2one('hr.employee', string='Expected Holder')
    found_location_id = fields.Many2one('asset.location', string='Found At')
    status = fields.Selection([
        ('pending', 'Pending'), ('found', 'Found'),
        ('misplaced', 'Found - Wrong Location'), ('missing', 'Missing')],
        default='pending', required=True)
    condition = fields.Selection([
        ('good', 'Good'), ('fair', 'Fair'), ('poor', 'Poor'), ('damaged', 'Damaged')])
    scanned_at = fields.Datetime(readonly=True)
    applied = fields.Boolean('Correction Applied', readonly=True)
    note = fields.Char()

    def _mark_found(self, location=False):
        for line in self:
            misplaced = bool(location and line.expected_location_id and location != line.expected_location_id)
            line.write({
                'status': 'misplaced' if misplaced else 'found',
                'found_location_id': (location or line.expected_location_id).id,
                'scanned_at': fields.Datetime.now(),
            })

    def action_found(self):
        self._mark_found(self.mapped('audit_id.scan_location_id')[:1])

    def action_missing(self):
        self.write({'status': 'missing', 'scanned_at': fields.Datetime.now()})
