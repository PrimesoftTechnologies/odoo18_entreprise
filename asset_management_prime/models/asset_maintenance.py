from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError


class AssetMaintenance(models.Model):
    _name = 'asset.maintenance'
    _description = 'Asset Maintenance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority desc, scheduled_date, id desc'

    reference = fields.Char(default='New', copy=False, readonly=True)
    name = fields.Char('Subject', required=True, tracking=True)
    asset_id = fields.Many2one('asset.asset', required=True, tracking=True, index=True,
                               domain="[('state', '!=', 'disposed'), ('state', '!=', 'draft')]")
    company_id = fields.Many2one('res.company', required=True,
                                 default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id')
    maintenance_type = fields.Selection([
        ('corrective', 'Corrective (Repair)'), ('preventive', 'Preventive (Service)')],
        default='corrective', required=True, tracking=True)
    priority = fields.Selection([('0', 'Normal'), ('1', 'High'), ('2', 'Urgent')], default='0')
    description = fields.Text('Problem / Work Description')
    requested_by_id = fields.Many2one('hr.employee', string='Requested By',
                                      default=lambda self: self.env.user.employee_id)
    technician_id = fields.Many2one('res.users', string='Technician', tracking=True)
    scheduled_date = fields.Date('Scheduled Date', tracking=True)
    start_date = fields.Datetime('Started On', readonly=True, copy=False)
    end_date = fields.Datetime('Finished On', readonly=True, copy=False)
    downtime_hours = fields.Float(compute='_compute_downtime', store=True)

    recurring = fields.Boolean('Recurring')
    interval_months = fields.Integer('Repeat Every (Months)', default=6)

    part_ids = fields.One2many('asset.maintenance.part', 'maintenance_id', string='Spare Parts')
    labor_cost = fields.Monetary(currency_field='currency_id', tracking=True)
    parts_cost = fields.Monetary(compute='_compute_costs', store=True, currency_field='currency_id')
    total_cost = fields.Monetary(compute='_compute_costs', store=True, currency_field='currency_id')
    vendor_id = fields.Many2one('res.partner', string='External Vendor')
    resolution = fields.Text('Resolution Notes')

    state = fields.Selection([
        ('new', 'New'), ('in_progress', 'In Progress'),
        ('done', 'Done'), ('cancel', 'Cancelled')],
        default='new', tracking=True, copy=False, required=True)

    is_overdue = fields.Boolean(compute='_compute_is_overdue')

    def _compute_is_overdue(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.is_overdue = bool(rec.state == 'new' and rec.scheduled_date and rec.scheduled_date < today)

    @api.depends('part_ids.subtotal', 'labor_cost')
    def _compute_costs(self):
        for rec in self:
            rec.parts_cost = sum(rec.part_ids.mapped('subtotal'))
            rec.total_cost = rec.parts_cost + rec.labor_cost

    @api.depends('start_date', 'end_date')
    def _compute_downtime(self):
        for rec in self:
            if rec.start_date and rec.end_date:
                rec.downtime_hours = (rec.end_date - rec.start_date).total_seconds() / 3600.0
            else:
                rec.downtime_hours = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', 'New') == 'New':
                vals['reference'] = self.env['ir.sequence'].next_by_code('asset.maintenance') or 'New'
        return super().create(vals_list)

    def action_start(self):
        for rec in self:
            if rec.state != 'new':
                continue
            rec.write({'state': 'in_progress', 'start_date': fields.Datetime.now()})
            asset = rec.asset_id.sudo()
            if asset.state in ('available', 'in_use'):
                asset.state = 'maintenance'
            asset.message_post(body=self.env._("Maintenance %s started.", rec.reference))

    def action_done(self):
        for rec in self:
            if rec.state not in ('new', 'in_progress'):
                continue
            if not rec.start_date:
                rec.start_date = fields.Datetime.now()
            rec.write({'state': 'done', 'end_date': fields.Datetime.now()})
            asset = rec.asset_id.sudo()
            others = self.search_count([
                ('asset_id', '=', asset.id), ('state', '=', 'in_progress'), ('id', '!=', rec.id)])
            if not others:
                asset.action_set_available_from_maint()
            asset.message_post(body=self.env._(
                "Maintenance %(ref)s completed. Cost: %(cost)s", ref=rec.reference, cost=rec.total_cost))
            if rec.recurring and rec.maintenance_type == 'preventive' and rec.interval_months > 0:
                base = rec.scheduled_date or fields.Date.context_today(rec)
                rec.copy({
                    'scheduled_date': base + relativedelta(months=rec.interval_months),
                    'state': 'new',
                })

    def action_cancel(self):
        for rec in self:
            if rec.state == 'in_progress':
                others = self.search_count([
                    ('asset_id', '=', rec.asset_id.id), ('state', '=', 'in_progress'), ('id', '!=', rec.id)])
                if not others:
                    rec.asset_id.sudo().action_set_available_from_maint()
            rec.state = 'cancel'


class AssetMaintenancePart(models.Model):
    _name = 'asset.maintenance.part'
    _description = 'Maintenance Spare Part'

    maintenance_id = fields.Many2one('asset.maintenance', required=True, ondelete='cascade')
    currency_id = fields.Many2one(related='maintenance_id.currency_id')
    name = fields.Char('Part / Description', required=True)
    quantity = fields.Float(default=1.0)
    unit_cost = fields.Monetary(currency_field='currency_id')
    subtotal = fields.Monetary(compute='_compute_subtotal', store=True, currency_field='currency_id')

    @api.depends('quantity', 'unit_cost')
    def _compute_subtotal(self):
        for rec in self:
            rec.subtotal = rec.quantity * rec.unit_cost
