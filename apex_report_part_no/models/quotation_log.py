from odoo import _, api, fields, models


class ApexQuotationLog(models.Model):
    _name = 'apex.quotation.log'
    _description = 'Quotation Analytic Log'
    _order = 'id desc'
    _rec_name = 'order_name'

    date = fields.Datetime(string='Date', default=fields.Datetime.now, readonly=True, index=True)
    order_id = fields.Many2one('sale.order', string='Quotation', ondelete='set null', index=True, readonly=True)
    order_name = fields.Char(string='Quotation No.', readonly=True, index=True)
    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True)
    user_id = fields.Many2one('res.users', string='Changed By', readonly=True, index=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    action = fields.Selection([
        ('create', 'Quotation Created'),
        ('update', 'Quotation Updated'),
        ('state', 'Status Changed'),
        ('line_add', 'Line Added'),
        ('line_update', 'Line Updated'),
        ('line_delete', 'Line Removed'),
        ('delete', 'Quotation Deleted'),
    ], string='Action', readonly=True, index=True)
    field_label = fields.Char(string='Field', readonly=True)
    line_name = fields.Char(string='Product / Line', readonly=True)
    old_value = fields.Text(string='Old Value', readonly=True)
    new_value = fields.Text(string='New Value', readonly=True)
    description = fields.Text(string='Description', readonly=True)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @api.model
    def _log(self, order, action, description, field_label=False, old=False, new=False, line_name=False):
        """Create a log entry (always as sudo, so any salesperson can generate logs)."""
        self.sudo().create({
            'order_id': order.id,
            'order_name': order.name,
            'partner_id': order.partner_id.id,
            'company_id': order.company_id.id,
            'user_id': self.env.user.id,
            'action': action,
            'description': description,
            'field_label': field_label,
            'line_name': line_name,
            'old_value': old,
            'new_value': new,
        })

    @api.model
    def _format_value(self, record, fname):
        field = record._fields[fname]
        value = record[fname]
        if field.type == 'many2one':
            return value.display_name or ''
        if field.type in ('many2many', 'one2many'):
            return ', '.join(value.mapped('display_name'))
        if field.type == 'selection':
            return dict(field._description_selection(record.env)).get(value, value or '') or ''
        if field.type == 'boolean':
            return _('Yes') if value else _('No')
        if field.type in ('float', 'monetary'):
            return '%.2f' % (value or 0.0)
        if field.type in ('date', 'datetime'):
            return fields.Datetime.to_string(value) if value else ''
        if value in (False, None):
            return ''
        return str(value)

    @api.model
    def _snapshot(self, record, fnames):
        return {f: self._format_value(record, f) for f in fnames if f in record._fields}
