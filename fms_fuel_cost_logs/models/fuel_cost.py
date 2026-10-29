from odoo import api, fields, models


class FmsFuelCost(models.Model):
    _name = 'fms.fuel.cost'
    _description = 'Fuel Cost Log'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(string='Reference', default='New', copy=False, readonly=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today, tracking=True)
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', required=True, tracking=True)
    driver_id = fields.Many2one('res.partner', string='Driver', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
    line_ids = fields.One2many('fms.fuel.cost.line', 'cost_id', string='Fuel Details', copy=True)
    total_quantity = fields.Float(string='Total Liters', compute='_compute_totals', store=True)
    total_cost = fields.Monetary(string='Total Cost', compute='_compute_totals', store=True,
                                 currency_field='currency_id')
    notes = fields.Text(string='Notes')

    @api.depends('line_ids.quantity', 'line_ids.total_cost')
    def _compute_totals(self):
        for rec in self:
            rec.total_quantity = sum(rec.line_ids.mapped('quantity'))
            rec.total_cost = sum(rec.line_ids.mapped('total_cost'))

    @api.onchange('vehicle_id')
    def _onchange_vehicle_id(self):
        if self.vehicle_id:
            self.driver_id = self.vehicle_id.driver_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('fms.fuel.cost') or 'New'
        return super().create(vals_list)


class FmsFuelCostLine(models.Model):
    _name = 'fms.fuel.cost.line'
    _description = 'Fuel Cost Line'

    cost_id = fields.Many2one('fms.fuel.cost', string='Fuel Cost', required=True, ondelete='cascade')
    currency_id = fields.Many2one('res.currency', related='cost_id.currency_id', readonly=True)
    description = fields.Char(string='Description', required=True)
    quantity = fields.Float(string='Fuel Quantity (Liters)', default=0.0)
    unit_price = fields.Monetary(string='Unit Price', currency_field='currency_id')
    total_cost = fields.Monetary(string='Total Cost', compute='_compute_total_cost', store=True,
                                 currency_field='currency_id')
    partner_id = fields.Many2one('res.partner', string='Supplier / Fuel Station')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')

    @api.depends('quantity', 'unit_price')
    def _compute_total_cost(self):
        for line in self:
            line.total_cost = line.quantity * line.unit_price
