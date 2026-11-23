from datetime import datetime, time

from odoo import api, fields, models, _


class TimberDashboard(models.TransientModel):
    """Dashboard cards. It stores nothing: every number is read live from
    standard Odoo models (Lots, Manufacturing, Purchase, Landed Costs)."""
    _name = 'timber.dashboard'
    _description = 'Timber Dashboard'

    name = fields.Char(default='Timber Dashboard')
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id)
    filter_from_date = fields.Date(string='From Date')
    filter_to_date = fields.Date(string='To Date')

    total_logs = fields.Integer(compute='_compute_metrics')
    total_log_cbm = fields.Float(compute='_compute_metrics', digits=(16, 4))
    total_sawing_orders = fields.Integer(compute='_compute_metrics')
    total_board_cbm = fields.Float(compute='_compute_metrics', digits=(16, 4))
    total_waste_cbm = fields.Float(compute='_compute_metrics', digits=(16, 4))
    total_purchase_amount = fields.Monetary(compute='_compute_metrics')
    total_operational_expense = fields.Monetary(compute='_compute_metrics')
    grand_total_operations_cost = fields.Monetary(compute='_compute_metrics')
    board_ratio_label = fields.Char(compute='_compute_metrics')
    waste_ratio_label = fields.Char(compute='_compute_metrics')

    # ------------------------------------------------------------------
    def _range(self, field_name, is_datetime=True):
        self.ensure_one()
        domain = []
        if self.filter_from_date:
            value = datetime.combine(self.filter_from_date, time.min) if is_datetime else self.filter_from_date
            domain.append((field_name, '>=', value))
        if self.filter_to_date:
            value = datetime.combine(self.filter_to_date, time.max) if is_datetime else self.filter_to_date
            domain.append((field_name, '<=', value))
        return domain

    def _lot_domain(self):
        return [('product_id.timber_type', '=', 'log')] + self._range('create_date')

    def _mo_domain(self):
        return [('product_id.timber_type', '=', 'board')] + self._range('date_start')

    def _po_line_domain(self):
        return [
            ('product_id.timber_type', '=', 'log'),
            ('order_id.state', 'in', ('purchase', 'done')),
        ] + self._range('order_id.date_order')

    def _cost_domain(self):
        return [
            ('state', '=', 'done'),
            ('picking_ids.move_ids.product_id.timber_type', '=', 'log'),
        ] + self._range('date', is_datetime=False)

    @api.depends('filter_from_date', 'filter_to_date')
    def _compute_metrics(self):
        for rec in self:
            lots = self.env['stock.lot'].search(rec._lot_domain())
            mos = self.env['mrp.production'].search(rec._mo_domain())
            po_lines = self.env['purchase.order.line'].search(rec._po_line_domain())
            costs = self.env['stock.landed.cost'].search(rec._cost_domain())

            rec.total_logs = len(lots)
            rec.total_log_cbm = sum(lots.mapped('timber_cbm'))
            rec.total_sawing_orders = len(mos)
            rec.total_board_cbm = sum(mos.mapped('timber_board_cbm'))
            rec.total_waste_cbm = sum(mos.mapped('timber_waste_cbm'))
            rec.total_purchase_amount = sum(po_lines.mapped('price_subtotal'))
            rec.total_operational_expense = sum(costs.mapped('amount_total'))
            rec.grand_total_operations_cost = (
                rec.total_purchase_amount + rec.total_operational_expense)

            # Ratios shown on the cards come from the Bill of Materials
            board_pct = waste_pct = 0.0
            bom = self.env['mrp.bom'].search(
                [('product_tmpl_id.timber_type', '=', 'board')], limit=1)
            if bom:
                log_qty = sum(bom.bom_line_ids.filtered(
                    lambda l: l.product_id.timber_type == 'log').mapped('product_qty'))
                if log_qty:
                    board_pct = bom.product_qty / log_qty * 100.0
                    waste_pct = sum(bom.byproduct_ids.mapped('product_qty')) / log_qty * 100.0
            rec.board_ratio_label = _('%d%% Ratio', round(board_pct))
            rec.waste_ratio_label = _('%d%% Ratio', round(waste_pct))

    # ---- "View" links on the cards open the standard lists -------------
    def _open(self, name, model, domain):
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': model,
            'view_mode': 'list,form',
            'domain': domain,
        }

    def action_view_logs(self):
        self.ensure_one()
        return self._open(_('Log Lots'), 'stock.lot', self._lot_domain())

    def action_view_sawing(self):
        self.ensure_one()
        return self._open(_('Sawing Orders'), 'mrp.production', self._mo_domain())

    def action_view_purchases(self):
        self.ensure_one()
        return self._open(
            _('Log Purchase Lines'), 'purchase.order.line', self._po_line_domain())

    def action_view_expenses(self):
        self.ensure_one()
        return self._open(
            _('Expenses (Landed Costs)'), 'stock.landed.cost', self._cost_domain())
