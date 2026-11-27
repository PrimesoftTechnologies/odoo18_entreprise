# -*- coding: utf-8 -*-
import base64
import re

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from ..report.aging_xlsx import DetailedAgingXlsx, SimpleAgingXlsx


class StockAgingReport(models.TransientModel):
    _name = 'stock.aging.report'
    _description = 'Stock Aging Report'

    # Same conventions as the valuation wizard: no field-level domain on the
    # relational parameters (a domain filters what is *read*), validation on
    # the server, domains in the view.
    simple_report = fields.Boolean(
        string='Simple Report', default=True,
        help="Simple: one row per product and warehouse, aged from the last receipt date (classic layout).\n"
             "Off = Detailed: receipt-layer aging, demand, dead stock, risk and management analytics.")
    company_ids = fields.Many2many(
        'res.company', 'stock_aging_report_company_rel', 'wizard_id', 'company_id', string='Companies',
        default=lambda self: self.env.company)
    as_of = fields.Date(string='As at Date', required=True, default=fields.Date.context_today,
                        help="Stock and values at the end of this day (your time zone).")
    warehouse_ids = fields.Many2many('stock.warehouse', string='Warehouses',
                                     help="Leave empty for all warehouses.")
    location_ids = fields.Many2many('stock.location', string='Locations',
                                    help="Leave empty for all. Sub-locations are included.")
    category_ids = fields.Many2many('product.category', string='Product Categories',
                                    help="Sub-categories are included.")
    product_ids = fields.Many2many('product.product', string='Products')
    lot_ids = fields.Many2many('stock.lot', string='Lots / Serial Numbers')
    cost_method = fields.Selection([
        ('all', 'All'), ('standard', 'Standard Price'), ('average', 'Average Cost (AVCO)'),
        ('fifo', 'First In First Out (FIFO)')], string='Costing Method', required=True, default='all')
    include_zero = fields.Boolean(string='Include Zero-Stock Products', default=False)
    include_archived = fields.Boolean(string='Include Archived Products', default=True,
                                      help="Archived products can still hold stock value.")
    include_negative = fields.Boolean(string='Include Negative Stock', default=True,
                                      help="Negative stock is shown as an exception (it has no age).")
    # detailed settings
    bucket_1 = fields.Integer(string='Bucket 1 up to (days)', default=30)
    bucket_2 = fields.Integer(string='Bucket 2 up to (days)', default=60)
    bucket_3 = fields.Integer(string='Bucket 3 up to (days)', default=90)
    bucket_4 = fields.Integer(string='Bucket 4 up to (days)', default=180)
    bucket_5 = fields.Integer(string='Bucket 5 up to (days)', default=365)
    slow_days = fields.Integer(string='Slow-Moving after (days)', default=90,
                               help="No customer sale or production consumption for this many days.")
    nonmoving_days = fields.Integer(string='Non-Moving after (days)', default=180)
    analysis_days = fields.Integer(string='Demand History (days)', default=365,
                                   help="Period used for consumption, frequency and coverage.")
    overstock_months = fields.Integer(string='Overstock above (months of cover)', default=12)
    expiry_days = fields.Integer(string='Expiry Warning (days)', default=90)
    min_age_days = fields.Selection([
        ('0', 'All ages'), ('30', 'Older than 30 days'), ('90', 'Older than 90 days'),
        ('180', 'Older than 180 days'), ('365', 'Older than 365 days')],
        string='Detail Lists Show', default='0', required=True,
        help="Filters the receipt-level list only. Totals, KPIs and reconciliation always cover all stock.")
    top_n = fields.Integer(string='Rows per PDF Table', default=25)

    file_name = fields.Char(readonly=True)
    data = fields.Binary(readonly=True, attachment=False)

    @api.constrains('bucket_1', 'bucket_2', 'bucket_3', 'bucket_4', 'bucket_5', 'slow_days', 'nonmoving_days')
    def _check_settings(self):
        for rec in self:
            b = [rec.bucket_1, rec.bucket_2, rec.bucket_3, rec.bucket_4, rec.bucket_5]
            if any(x <= 0 for x in b) or b != sorted(set(b)):
                raise ValidationError(_("Aging buckets must be increasing numbers of days."))
            if rec.nonmoving_days < rec.slow_days:
                raise ValidationError(_("Non-moving days must be at least the slow-moving days."))

    @api.onchange('company_ids')
    def _onchange_company_ids(self):
        self.warehouse_ids = self.warehouse_ids.filtered(lambda w: w.company_id in self.company_ids)
        self.location_ids = self.location_ids.filtered(lambda l: l.company_id in self.company_ids)

    def _get_companies(self):
        self.ensure_one()
        return self.env['res.company'].browse(self.sudo().company_ids.ids)

    def _get_engine_params(self):
        self.ensure_one()
        companies = self._get_companies()
        if not companies:
            raise UserError(_("Select at least one company."))
        if companies - self.env.user.company_ids:
            raise AccessError(_("You are not allowed to access the selected companies."))
        sel = self.with_context(active_test=False)
        if sel.location_ids.filtered(lambda l: l.company_id not in companies) or \
                sel.warehouse_ids.filtered(lambda w: w.company_id not in companies):
            raise UserError(_("Every selected warehouse and location must belong to one of the selected companies."))
        return {
            'company_ids': companies.ids, 'as_of': self.as_of,
            'tz': self.env.context.get('tz') or self.env.user.tz or 'UTC',
            'mode': 'simple' if self.simple_report else 'detailed',
            'warehouse_ids': sel.warehouse_ids.ids, 'location_ids': sel.location_ids.ids,
            'category_ids': sel.category_ids.ids, 'product_ids': sel.product_ids.ids, 'lot_ids': sel.lot_ids.ids,
            'cost_method': self.cost_method, 'include_zero': self.include_zero,
            'include_archived': self.include_archived, 'include_negative': self.include_negative,
            'thresholds': [self.bucket_1, self.bucket_2, self.bucket_3, self.bucket_4, self.bucket_5],
            'slow_days': self.slow_days, 'nonmoving_days': self.nonmoving_days,
            'analysis_days': self.analysis_days, 'overstock_months': self.overstock_months,
            'expiry_days': self.expiry_days, 'min_age_days': int(self.min_age_days or 0), 'top_n': self.top_n,
        }

    def _get_report_dataset(self):
        self.ensure_one()
        params = self._get_engine_params()
        return self.env['eg.stock.aging.engine'].with_context(
            allowed_company_ids=params['company_ids'])._build_dataset(params)

    def _file_name(self, ext):
        companies = self._get_companies()
        name = companies[0].name if len(companies) == 1 else 'Multi-company'
        slug = re.sub(r'[^A-Za-z0-9]+', '_', name).strip('_') or 'Company'
        return 'Stock_Aging_%s_%s_%s.%s' % ('Simple' if self.simple_report else 'Detailed', slug, self.as_of, ext)

    def action_print_pdf(self):
        self.ensure_one()
        self._get_engine_params()
        xmlid = 'eg_inventory_valuation_report.action_aging_simple' if self.simple_report \
            else 'eg_inventory_valuation_report.action_aging_detailed'
        return self.env.ref(xmlid).report_action(self)

    def action_export_xlsx(self):
        self.ensure_one()
        dataset = self._get_report_dataset()
        renderer = SimpleAgingXlsx if self.simple_report else DetailedAgingXlsx
        content = renderer(self.env, dataset).render()
        filename = self._file_name('xlsx')
        self.write({'file_name': filename, 'data': base64.b64encode(content)})
        return {'type': 'ir.actions.act_url', 'target': 'self',
                'url': '/web/content/stock.aging.report/%s/data/%s?download=true' % (self.id, filename)}
