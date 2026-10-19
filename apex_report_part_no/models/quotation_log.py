from odoo import _, api, fields, models


class ApexQuotationLog(models.Model):
    _name = 'apex.quotation.log'
    _description = 'Quotation Analytic Log'
    _order = 'id desc'
    _rec_name = 'order_name'

    # --- Requested columns -------------------------------------------------
    order_id = fields.Many2one('sale.order', string='Quotation', ondelete='set null', index=True, readonly=True)
    order_name = fields.Char(string='Quotation No.', readonly=True, index=True)
    partner_id = fields.Many2one('res.partner', string='Customer Name', readonly=True)
    product_name = fields.Char(string='Product Name', readonly=True)
    part_no = fields.Char(string='Part No.', readonly=True)
    quantity = fields.Float(string='Quantity', digits='Product Unit of Measure', readonly=True)
    uom_id = fields.Many2one('uom.uom', string='UoM', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
    unit_price = fields.Monetary(string='Unit Price', currency_field='currency_id', readonly=True)
    total_amount = fields.Monetary(string='Total Amount', currency_field='currency_id', readonly=True)
    reason_lost = fields.Text(string='Reason for LOST', readonly=True)

    # --- Extra information -------------------------------------------------
    action = fields.Selection([
        ('line_add', 'Product Added'),
        ('line_update', 'Product Updated'),
        ('line_delete', 'Product Removed'),
    ], string='Action', readonly=True, index=True)
    changes = fields.Text(string='What Changed', readonly=True)
    user_id = fields.Many2one('res.users', string='Changed By', readonly=True, index=True)
    date = fields.Datetime(string='Date', default=fields.Datetime.now, readonly=True, index=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)

    # ------------------------------------------------------------------
    @api.model
    def _log_line(self, line, action, reason=False, changes=False):
        """Write one log row describing a quotation line (always as sudo)."""
        order = line.order_id
        uom = line.product_uom if 'product_uom' in line._fields else line.product_uom_id
        self.sudo().create({
            'order_id': order.id,
            'order_name': order.name,
            'partner_id': order.partner_id.id,
            'company_id': order.company_id.id,
            'product_name': line.product_id.name or line.name or '',
            'part_no': line.product_id.default_code or '',
            'quantity': line.product_uom_qty,
            'uom_id': uom.id,
            'currency_id': order.currency_id.id,
            'unit_price': line.price_unit,
            'total_amount': line.price_subtotal,
            'reason_lost': reason or False,
            'action': action,
            'changes': changes or False,
            'user_id': self.env.user.id,
        })

    @api.model
    def _format_value(self, record, fname):
        field = record._fields[fname]
        value = record[fname]
        if field.type == 'many2one':
            return value.display_name or ''
        if field.type in ('many2many', 'one2many'):
            return ', '.join(value.mapped('display_name'))
        if field.type in ('float', 'monetary'):
            return '%.2f' % (value or 0.0)
        if value in (False, None):
            return ''
        return str(value)

    @api.model
    def _snapshot(self, record, fnames):
        return {f: self._format_value(record, f) for f in fnames if f in record._fields}
