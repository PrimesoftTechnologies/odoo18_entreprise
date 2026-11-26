# -*- coding: utf-8 -*-
import base64
import re

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from ..report.valuation_xlsx import InventoryValuationXlsx


class InventoryValuationReport(models.TransientModel):
    _name = 'inventory.valuation.report'
    _description = 'Inventory Valuation Report'

    # ------------------------------------------------------------------
    # Parameters
    # ------------------------------------------------------------------
    # Legacy single-company field (kept for API compatibility). Only used
    # as a fallback when ``company_ids`` is empty.
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    # NOTE: no field-level domains on the relational parameters below. Odoo
    # applies an x2many field's domain when *reading* it, which would silently
    # drop a forbidden or non-matching selection instead of refusing it.
    # Domains live in the view; the server validates the stored selection.
    company_ids = fields.Many2many(
        'res.company', 'inventory_valuation_report_company_rel', 'wizard_id', 'company_id',
        string='Companies', default=lambda self: self.env.company,
        help="Report several companies side by side. Each company is valued in its own currency; "
             "totals are never added across currencies.")
    report_type = fields.Selection([
        ('period', 'Movements over a period'),
        ('as_of', 'Valuation as of a date'),
    ], string='Report Type', required=True, default='period',
        help="Period: opening balance, incoming, outgoing, adjustments and closing balance.\n"
             "As of a date: stock quantity and value at the end of the chosen date.")
    start_date = fields.Date(string='Start Date', default=lambda self: fields.Date.context_today(self).replace(day=1))
    end_date = fields.Date(string='End Date', required=True, default=fields.Date.context_today,
                           help="Balances are taken at the end of this day (in your time zone).")
    date_basis = fields.Selection([
        ('valuation', 'Inventory valuation date'),
        ('accounting', 'Journal entry date'),
    ], string='Date Basis', required=True, default='valuation',
        help="Inventory valuation date: when the stock was valued (identical to Odoo's Valuation report).\n"
             "Journal entry date: accounting date of the related journal entry, for automated valuation "
             "(useful when entries are back-dated, e.g. inventory adjustments with an accounting date).")
    scope = fields.Selection([
        ('company', 'Company'),
        ('warehouse', 'Per warehouse'),
        ('location', 'Selected locations'),
    ], string='Level', required=True, default='company',
        help="Company: authoritative valuation from Odoo's valuation layers.\n"
             "Per warehouse / locations: quantities per location with values ALLOCATED at company "
             "average cost (Odoo values stock per company, not per location). Clearly marked as estimated.")
    warehouse_ids = fields.Many2many('stock.warehouse', string='Warehouses',
                                     help="Leave empty for all warehouses (plus locations outside warehouses).")
    location_ids = fields.Many2many('stock.location', string='Locations',
                                    help="Sub-locations are included automatically.")
    category_ids = fields.Many2many('product.category', string='Product Categories',
                                    help="Sub-categories are included automatically.")
    product_ids = fields.Many2many('product.product', string='Products')
    cost_method = fields.Selection([
        ('all', 'All'),
        ('standard', 'Standard Price'),
        ('average', 'Average Cost (AVCO)'),
        ('fifo', 'First In First Out (FIFO)'),
    ], string='Costing Method', required=True, default='all')
    valuation_type = fields.Selection([
        ('all', 'Manual and automated'),
        ('real_time', 'Automated only'),
        ('manual_periodic', 'Manual only'),
    ], string='Inventory Valuation', required=True, default='all')
    stock_filter = fields.Selection([
        ('active', 'With a balance or movement'),
        ('nonzero', 'Non-zero closing balance only'),
        ('all', 'All storable products'),
    ], string='Products to Show', required=True, default='active')
    include_archived = fields.Boolean(
        string='Include Archived Products', default=True,
        help="Archived products can still hold stock value. Excluding them makes totals differ "
             "from the company valuation.")
    detail_level = fields.Selection([
        ('detailed', 'Detailed (per product)'),
        ('summary', 'Summary (per category)'),
    ], string='Detail Level', required=True, default='detailed')
    filter_by = fields.Selection([
        ('category', 'Product category'),
        ('product', 'No grouping'),
    ], string='Group By', required=True, default='category',
        help="Category: category sections with subtotals. No grouping: one product list per section.")

    file_name = fields.Char(string='File Name', readonly=True)
    data = fields.Binary('Download Report', readonly=True, attachment=False)

    # ------------------------------------------------------------------
    # UI helpers
    # ------------------------------------------------------------------
    def _get_companies(self):
        """Selected companies, read without record-rule filtering so that a
        company the user may not access is *refused*, never silently dropped."""
        self.ensure_one()
        raw = self.sudo()
        companies = raw.company_ids or raw.company_id
        return self.env['res.company'].browse(companies.ids)

    @api.onchange('company_ids')
    def _onchange_company_ids(self):
        self.location_ids = self.location_ids.filtered(lambda l: l.company_id in self.company_ids)
        self.warehouse_ids = self.warehouse_ids.filtered(lambda w: w.company_id in self.company_ids)

    @api.constrains('start_date', 'end_date', 'report_type')
    def _check_dates(self):
        for rec in self:
            if rec.report_type == 'period':
                if not rec.start_date:
                    raise ValidationError(_("Please set a start date."))
                if rec.start_date > rec.end_date:
                    raise ValidationError(_("The end date must be on or after the start date."))

    # ------------------------------------------------------------------
    # Dataset (single source for PDF and XLSX)
    # ------------------------------------------------------------------
    def _get_engine_params(self):
        self.ensure_one()
        companies = self._get_companies()
        if not companies:
            raise UserError(_("Select at least one company."))
        user_companies = self.env.user.company_ids
        if companies - user_companies:
            raise AccessError(_("You are not allowed to access the selected companies."))
        if self.scope == 'location':
            if not self.location_ids:
                raise UserError(_("Select at least one location."))
            if self.with_context(active_test=False).location_ids.filtered(lambda l: l.company_id not in companies):
                raise UserError(_("Every selected location must belong to one of the selected companies."))
        if self.scope == 'warehouse' and self.warehouse_ids.filtered(lambda w: w.company_id not in companies):
            raise UserError(_("Every selected warehouse must belong to one of the selected companies."))
        sel = self.with_context(active_test=False)
        return {
            'company_ids': companies.ids,
            'report_type': self.report_type,
            'date_from': self.start_date,
            'date_to': self.end_date,
            'date_basis': self.date_basis,
            'tz': self.env.context.get('tz') or self.env.user.tz or 'UTC',
            'scope': self.scope,
            # active_test=False: an archived product/location explicitly
            # selected by the user must not silently disappear from the report.
            'warehouse_ids': sel.warehouse_ids.ids if self.scope == 'warehouse' else [],
            'location_ids': sel.location_ids.ids if self.scope == 'location' else [],
            'category_ids': sel.category_ids.ids,
            'product_ids': sel.product_ids.ids,
            'cost_method': self.cost_method,
            'valuation_type': self.valuation_type,
            'stock_filter': self.stock_filter,
            'include_archived': self.include_archived,
            'detail_level': self.detail_level,
            'group_by': 'category' if self.filter_by == 'category' else 'none',
        }

    def _get_report_dataset(self):
        self.ensure_one()
        self._check_dates()
        params = self._get_engine_params()  # validates companies, locations, warehouses
        engine = self.env['eg.inventory.valuation.engine'].with_context(
            allowed_company_ids=params['company_ids'])
        return engine._build_dataset(params)

    def _report_filename(self, ext):
        self.ensure_one()
        companies = self._get_companies()
        name = companies[0].name if len(companies) == 1 else 'Multi-company'
        slug = re.sub(r'[^A-Za-z0-9]+', '_', name).strip('_') or 'Company'
        if self.report_type == 'period':
            period = '%s_%s' % (self.start_date, self.end_date)
        else:
            period = 'as_of_%s' % self.end_date
        return 'Inventory_Valuation_%s_%s.%s' % (slug, period, ext)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_print_pdf(self):
        self.ensure_one()
        self._get_engine_params()  # validate before rendering
        return self.env.ref('eg_inventory_valuation_report.stock_inventory_pdf_report_report').report_action(self)

    def action_export_xlsx(self):
        self.ensure_one()
        dataset = self._get_report_dataset()
        content = InventoryValuationXlsx(self.env, dataset).render()
        filename = self._report_filename('xlsx')
        self.write({'file_name': filename, 'data': base64.b64encode(content)})
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/inventory.valuation.report/%s/data/%s?download=true' % (self.id, filename),
            'target': 'self',
        }

    def action_export_xls(self):
        """Backward compatible entry point (old 'Export XLS' button)."""
        return self.action_export_xlsx()

    def get_report_data(self):
        """Backward compatible API: returns the report dataset."""
        return self._get_report_dataset()
