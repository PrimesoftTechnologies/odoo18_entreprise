from odoo import _, api, fields, models

QUOTATION_STATES = ('draft', 'sent')

# Technical / noisy fields that are never logged on the quotation header
ORDER_SKIP_FIELDS = {
    'write_date', 'write_uid', 'create_date', 'create_uid', '__last_update',
    'message_main_attachment_id', 'access_token', 'signature', 'signed_by', 'signed_on',
    'invoice_status', 'locked', 'transaction_ids', 'authorized_transaction_ids',
}

# Quotation line fields that are logged
LINE_LOG_FIELDS = [
    'product_id', 'name', 'product_uom_qty', 'product_uom', 'price_unit',
    'discount', 'tax_id', 'customer_lead',
]


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    apex_log_count = fields.Integer(compute='_compute_apex_log_count')

    def _compute_apex_log_count(self):
        log = self.env['apex.quotation.log'].sudo()
        for order in self:
            order.apex_log_count = log.search_count([('order_id', '=', order.id)])

    def action_open_apex_logs(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Quotation Analytic Logs"),
            'res_model': 'apex.quotation.log',
            'view_mode': 'list,form,pivot,graph',
            'domain': [('order_id', '=', self.id)],
        }

    def _apex_loggable_fields(self, vals):
        result = []
        for fname in vals:
            field = self._fields.get(fname)
            if (field and field.store and fname not in ORDER_SKIP_FIELDS
                    and field.type not in ('one2many', 'binary')
                    and not fname.startswith('message_')):
                result.append(fname)
        return result

    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        if not self.env.context.get('install_mode'):
            log = self.env['apex.quotation.log']
            for order in orders.filtered(lambda o: o.state in QUOTATION_STATES):
                log._log(order, 'create', _("Quotation %s was created.", order.name or ''))
        return orders

    def write(self, vals):
        if self.env.context.get('install_mode'):
            return super().write(vals)
        fnames = self._apex_loggable_fields(vals)
        if 'order_line' in vals:
            fnames.append('amount_total')
        quotes = self.filtered(lambda o: o.state in QUOTATION_STATES) if fnames else self.browse()
        log = self.env['apex.quotation.log']
        before = {o.id: log._snapshot(o, fnames) for o in quotes}
        res = super().write(vals)
        for order in quotes.exists():
            after = log._snapshot(order, fnames)
            for fname in fnames:
                old, new = before[order.id].get(fname, ''), after.get(fname, '')
                if old == new:
                    continue
                label = self._fields[fname].string
                action = 'state' if fname == 'state' else 'update'
                log._log(order, action,
                         _("%(field)s changed from '%(old)s' to '%(new)s'", field=label, old=old or '-', new=new or '-'),
                         field_label=label, old=old, new=new)
        return res

    def unlink(self):
        if not self.env.context.get('install_mode'):
            log = self.env['apex.quotation.log']
            for order in self:
                log._log(order, 'delete', _("Quotation %s was deleted.", order.name or ''))
        return super().unlink()


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _apex_line_title(self):
        self.ensure_one()
        return self.product_id.display_name or self.name or _('Section / Note')

    def _apex_is_quotation_line(self):
        self.ensure_one()
        return self.order_id and self.order_id.state in QUOTATION_STATES

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        if not self.env.context.get('install_mode'):
            log = self.env['apex.quotation.log']
            for line in lines.filtered(lambda l: l._apex_is_quotation_line()):
                log._log(
                    line.order_id, 'line_add',
                    _("Line added: %(product)s (Qty: %(qty)s, Unit Price: %(price)s)",
                      product=line._apex_line_title(), qty=line.product_uom_qty, price=line.price_unit),
                    line_name=line._apex_line_title(),
                    new='%s x %s' % (line.product_uom_qty, line.price_unit))
        return lines

    def write(self, vals):
        if self.env.context.get('install_mode'):
            return super().write(vals)
        log = self.env['apex.quotation.log']
        fnames = [f for f in LINE_LOG_FIELDS if f in self._fields]
        quotes = self.filtered(lambda l: l._apex_is_quotation_line())
        before = {l.id: log._snapshot(l, fnames) for l in quotes}
        res = super().write(vals)
        for line in quotes.exists():
            after = log._snapshot(line, fnames)
            for fname in fnames:
                old, new = before[line.id].get(fname, ''), after.get(fname, '')
                if old == new or not line.order_id:
                    continue
                label = self._fields[fname].string
                log._log(
                    line.order_id, 'line_update',
                    _("%(product)s: %(field)s changed from '%(old)s' to '%(new)s'",
                      product=line._apex_line_title(), field=label, old=old or '-', new=new or '-'),
                    field_label=label, old=old, new=new, line_name=line._apex_line_title())
        return res

    def unlink(self):
        if not self.env.context.get('install_mode'):
            log = self.env['apex.quotation.log']
            for line in self.filtered(lambda l: l._apex_is_quotation_line()):
                log._log(
                    line.order_id, 'line_delete',
                    _("Line removed: %(product)s (Qty: %(qty)s, Unit Price: %(price)s)",
                      product=line._apex_line_title(), qty=line.product_uom_qty, price=line.price_unit),
                    line_name=line._apex_line_title(),
                    old='%s x %s' % (line.product_uom_qty, line.price_unit))
        return super().unlink()
