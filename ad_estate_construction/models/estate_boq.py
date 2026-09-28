from odoo import models, fields, api, _

class EstateDashboardConstruction(models.Model):
    _inherit = 'estate.dashboard'

    boq_count = fields.Integer(string='BOQ Count', compute='_compute_base_metrics')
    total_boq_cost = fields.Monetary(string='Total BOQ Estimated Cost', compute='_compute_base_metrics', currency_field='currency_id')

    @api.depends_context('uid')
    def _compute_base_metrics(self):
        super()._compute_base_metrics()
        for dash in self:
            boqs = self.env['estate.boq'].search([])
            dash.boq_count = len(boqs)
            dash.total_boq_cost = sum(boqs.mapped('total_estimated_cost'))


class EstateBoq(models.Model):

    _name = 'estate.boq'
    _description = 'Bill of Quantities (BOQ)'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='BOQ Title', required=True, tracking=True)
    project_id = fields.Many2one('estate.project', string='Project', required=True, tracking=True)
    building_id = fields.Many2one('estate.building', string='Building / Wing', domain="[('project_id', '=', project_id)]")
    wbs_phase = fields.Selection([
        ('substructure', 'Substructure / Foundation'),
        ('civil', 'Superstructure / Civil'),
        ('mep', 'MEP Services (Plumbing, Electrical, HVAC)'),
        ('finishes', 'Finishes & Interior Fit-outs')
    ], string='WBS Phase', default='civil', required=True, tracking=True)

    line_ids = fields.One2many('estate.boq.line', 'boq_id', string='BOQ Items')
    
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    overhead_pct = fields.Float(string='Overhead (%)', default=5.0)
    margin_pct = fields.Float(string='Margin (%)', default=10.0)

    subtotal_direct_cost = fields.Monetary(string='Direct Line Items Cost', compute='_compute_boq_totals', store=True, currency_field='currency_id')
    overhead_cost = fields.Monetary(string='Overhead Amount', compute='_compute_boq_totals', store=True, currency_field='currency_id')
    margin_cost = fields.Monetary(string='Margin Amount', compute='_compute_boq_totals', store=True, currency_field='currency_id')
    total_estimated_cost = fields.Monetary(string='Total Estimated Phase Cost', compute='_compute_boq_totals', store=True, currency_field='currency_id')

    @api.depends('line_ids.total_cost', 'overhead_pct', 'margin_pct')
    def _compute_boq_totals(self):
        for boq in self:
            direct = sum(boq.line_ids.mapped('total_cost'))
            boq.subtotal_direct_cost = direct
            boq.overhead_cost = direct * (boq.overhead_pct / 100.0)
            boq.margin_cost = direct * (boq.margin_pct / 100.0)
            boq.total_estimated_cost = direct + boq.overhead_cost + boq.margin_cost


class EstateBoqLine(models.Model):
    _name = 'estate.boq.line'
    _description = 'BOQ Line Item'

    boq_id = fields.Many2one('estate.boq', string='BOQ Reference', ondelete='cascade', required=True)
    product_id = fields.Many2one('product.product', string='Material / Item', required=True)
    description = fields.Char(string='Specification / Work Description')
    
    quantity = fields.Float(string='Estimated Quantity', default=1.0, required=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', related='product_id.uom_id', readonly=True)
    
    item_type = fields.Selection([
        ('material', 'Material'),
        ('labor', 'Labor'),
        ('equipment', 'Equipment Hire'),
        ('subcontract', 'Subcontract Work')
    ], string='Item Type', default='material', required=True)

    unit_rate = fields.Monetary(string='Unit Rate', currency_field='currency_id', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', related='boq_id.currency_id')
    total_cost = fields.Monetary(string='Total Cost', compute='_compute_total_cost', store=True, currency_field='currency_id')

    consumed_qty = fields.Float(string='Consumed Quantity', compute='_compute_consumed_qty', store=True)
    remaining_qty = fields.Float(string='Remaining Quantity', compute='_compute_consumed_qty', store=True)

    @api.depends('quantity', 'unit_rate')
    def _compute_total_cost(self):
        for line in self:
            line.total_cost = line.quantity * line.unit_rate

    @api.depends('quantity', 'boq_id')
    def _compute_consumed_qty(self):
        req_lines = self.env['estate.purchase.requisition.line'].search([
            ('boq_line_id', 'in', self.ids),
            ('requisition_id.state', 'in', ['approved', 'done'])
        ])
        consumed_map = {}
        for rl in req_lines:
            consumed_map[rl.boq_line_id.id] = consumed_map.get(rl.boq_line_id.id, 0.0) + rl.qty_requested

        for line in self:
            consumed = consumed_map.get(line.id, 0.0)
            line.consumed_qty = consumed
            line.remaining_qty = max(0.0, line.quantity - consumed)
