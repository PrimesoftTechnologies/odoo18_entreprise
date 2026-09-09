from odoo import models, fields, api
from datetime import timedelta

class SalonCommissionPayout(models.Model):
    _name = "salon.commission.payout"
    _description = "Employee Commission Payout & Deductions"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string="Reference", required=True, copy=False, readonly=True, default=lambda self: 'New')
    employee_id = fields.Many2one("hr.employee", string="Employee", required=True, tracking=True)
    date_from = fields.Date(string="Start Date", required=True)
    date_to = fields.Date(string="End Date", required=True)
    
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    
    gross_commission = fields.Monetary(
        string="Gross Commission", 
        compute="_compute_gross_commission", 
        store=True,
        currency_field="currency_id"
    )
    
    advance_deduction = fields.Monetary(
        string="Deductions / Advances Taken", 
        currency_field="currency_id",
        tracking=True,
        help="Amount taken in advance or deductions to subtract from total commission."
    )
    
    net_commission = fields.Monetary(
        string="Net Commission to Pay", 
        compute="_compute_net_commission", 
        store=True,
        currency_field="currency_id",
        tracking=True
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('paid', 'Paid')
    ], string='Status', default='draft', tracking=True)

    @api.depends('employee_id', 'date_from', 'date_to')
    def _compute_gross_commission(self):
        for record in self:
            if record.employee_id and record.date_from and record.date_to:
                date_from_dt = fields.Datetime.to_datetime(record.date_from)
                date_to_dt = fields.Datetime.to_datetime(record.date_to) + timedelta(days=1)
                
                domain = [
                    ('employee_id', '=', record.employee_id.id),
                    ('order_id.date_order', '>=', date_from_dt),
                    ('order_id.date_order', '<', date_to_dt),
                    ('commission_amount', '>', 0),
                ]
                lines = self.env['pos.order.line'].search(domain)
                record.gross_commission = sum(lines.mapped('commission_amount'))
            else:
                record.gross_commission = 0.0

    @api.onchange('employee_id', 'date_from', 'date_to')
    def _onchange_employee_dates(self):
        for record in self:
            if record.employee_id and record.date_from and record.date_to:
                date_from_dt = fields.Datetime.to_datetime(record.date_from)
                date_to_dt = fields.Datetime.to_datetime(record.date_to) + timedelta(days=1)
                
                domain = [
                    ('employee_id', '=', record.employee_id.id),
                    ('order_id.date_order', '>=', date_from_dt),
                    ('order_id.date_order', '<', date_to_dt),
                    ('commission_amount', '>', 0),
                ]
                lines = self.env['pos.order.line'].search(domain)
                record.gross_commission = sum(lines.mapped('commission_amount'))
            else:
                record.gross_commission = 0.0

    @api.depends('gross_commission', 'advance_deduction')
    def _compute_net_commission(self):
        for record in self:
            record.net_commission = record.gross_commission - record.advance_deduction

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('salon.commission.payout') or 'New'
        return super().create(vals)

    def action_mark_paid(self):
        self.write({'state': 'paid'})