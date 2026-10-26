from datetime import datetime, time

import pytz

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from ..models.store_expense import EXPENSE_CATEGORIES


class FredPlReportLine(models.Model):
    _name = 'fred.pl.report.line'
    _description = 'Phone Store P&L Line'
    _order = 'profit desc, id'

    wizard_id = fields.Many2one('fred.pl.report.wizard', ondelete='cascade')
    line_type = fields.Selection(
        [('product', 'Product'), ('expense', 'Expense')], required=True)
    name = fields.Char()
    qty = fields.Float(string='Qty')
    sales = fields.Monetary(string='Sales Price')
    cost = fields.Monetary(string='Cost Price')
    profit = fields.Monetary(string='Profit')
    margin = fields.Float(string='Margin %', compute='_compute_margin')
    currency_id = fields.Many2one(related='wizard_id.currency_id')

    @api.depends('sales', 'profit')
    def _compute_margin(self):
        for rec in self:
            rec.margin = (rec.profit / rec.sales * 100.0) if rec.sales else 0.0


class FredPlReportWizard(models.Model):
    _name = 'fred.pl.report.wizard'
    _description = 'Phone Store Profit and Loss'
    _order = 'id desc'

    name = fields.Char(string='Report', compute='_compute_name', store=True)
    date_from = fields.Date(
        required=True, default=lambda self: fields.Date.context_today(self).replace(day=1))
    date_to = fields.Date(required=True, default=fields.Date.context_today)
    config_ids = fields.Many2many(
        'pos.config', string='Shops',
        help='Leave empty to include all shops.')
    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id')

    line_ids = fields.One2many('fred.pl.report.line', 'wizard_id')
    product_line_ids = fields.One2many(
        'fred.pl.report.line', 'wizard_id', domain=[('line_type', '=', 'product')])
    expense_line_ids = fields.One2many(
        'fred.pl.report.line', 'wizard_id', domain=[('line_type', '=', 'expense')])

    total_sales = fields.Monetary(string='Sales Price')
    total_cost = fields.Monetary(string='Cost Price')
    gross_profit = fields.Monetary(string='Profit')
    total_expenses = fields.Monetary(string='Expenses')
    net_profit = fields.Monetary(string='Net Profit')
    margin = fields.Float(string='Net Margin %')

    @api.depends('date_from', 'date_to')
    def _compute_name(self):
        for rec in self:
            rec.name = _('Profit and Loss: %(f)s to %(t)s') % {
                'f': rec.date_from or '', 't': rec.date_to or ''}

    # ------------------------------------------------------------------
    def _get_utc_range(self):
        tz = pytz.timezone(self.env.user.tz or 'UTC')
        start = tz.localize(datetime.combine(self.date_from, time.min))
        end = tz.localize(datetime.combine(self.date_to, time.max))
        return (start.astimezone(pytz.utc).replace(tzinfo=None),
                end.astimezone(pytz.utc).replace(tzinfo=None))

    def _shop_names(self):
        self.ensure_one()
        return ', '.join(self.config_ids.mapped('name')) if self.config_ids else _('All shops')

    def action_generate(self):
        self.ensure_one()
        if self.date_from > self.date_to:
            raise UserError(_('"Date From" must be before "Date To".'))
        self.line_ids.unlink()
        start, end = self._get_utc_range()

        # ---------------- Sales & cost from POS ----------------
        domain = [
            ('order_id.state', 'in', ['paid', 'done', 'invoiced']),
            ('order_id.date_order', '>=', start),
            ('order_id.date_order', '<=', end),
            ('order_id.company_id', '=', self.company_id.id),
        ]
        if self.config_ids:
            domain.append(('order_id.config_id', 'in', self.config_ids.ids))
        pos_lines = self.env['pos.order.line'].search(domain)

        products = {}
        for line in pos_lines:
            cost = line.total_cost if 'total_cost' in line._fields else 0.0
            if not cost and line.product_id:
                cost = line.qty * line.product_id.with_company(
                    self.company_id).standard_price
            rec = products.setdefault(
                line.product_id.id,
                {'name': line.product_id.display_name or _('Unknown'),
                 'qty': 0.0, 'sales': 0.0, 'cost': 0.0})
            rec['qty'] += line.qty
            rec['sales'] += line.price_subtotal
            rec['cost'] += cost

        Line = self.env['fred.pl.report.line']
        vals_list = []
        total_sales = total_cost = 0.0
        for rec in products.values():
            total_sales += rec['sales']
            total_cost += rec['cost']
            vals_list.append({
                'wizard_id': self.id, 'line_type': 'product',
                'name': rec['name'], 'qty': rec['qty'],
                'sales': rec['sales'], 'cost': rec['cost'],
                'profit': rec['sales'] - rec['cost'],
            })

        # ---------------- Expenses ----------------
        exp_domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('company_id', '=', self.company_id.id),
        ]
        if self.config_ids:
            exp_domain += ['|', ('config_id', 'in', self.config_ids.ids),
                           ('config_id', '=', False)]
        labels = dict(EXPENSE_CATEGORIES)
        by_cat = {}
        for exp in self.env['fred.store.expense'].search(exp_domain):
            by_cat[exp.category] = by_cat.get(exp.category, 0.0) + exp.amount
        total_expenses = 0.0
        for cat, amount in by_cat.items():
            total_expenses += amount
            vals_list.append({
                'wizard_id': self.id, 'line_type': 'expense',
                'name': labels.get(cat, cat), 'sales': 0.0, 'cost': 0.0,
                'profit': amount,  # expense amount is stored in "profit" column
            })

        Line.create(vals_list)
        gross = total_sales - total_cost
        net = gross - total_expenses
        self.write({
            'total_sales': total_sales,
            'total_cost': total_cost,
            'gross_profit': gross,
            'total_expenses': total_expenses,
            'net_profit': net,
            'margin': (net / total_sales * 100.0) if total_sales else 0.0,
        })
        return True

    def action_print(self):
        self.ensure_one()
        self.action_generate()
        return self.env.ref(
            'fred_phone_store_application.action_report_phone_pl'
        ).report_action(self)
