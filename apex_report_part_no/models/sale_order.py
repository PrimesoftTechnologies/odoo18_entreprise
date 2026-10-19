from odoo import _, api, fields, models

QUOTATION_STATES = ('draft', 'sent')

# Line fields watched for "Product Updated" logs
LINE_WATCHED_FIELDS = [
    'product_id', 'product_uom_qty', 'product_uom', 'product_uom_id',
    'price_unit', 'discount',
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

    @api.model_create_multi
    def create(self, vals_list):
        # Nothing is logged while the quotation is being created (lines included).
        orders = super(SaleOrder, self.with_context(apex_no_line_log=True)).create(vals_list)
        return orders.with_context(apex_no_line_log=False)

    def unlink(self):
        # Deleting a whole quotation must not log every line.
        return super(SaleOrder, self.with_context(apex_no_line_log=True)).unlink()


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _apex_is_loggable(self):
        self.ensure_one()
        return bool(self.order_id) and self.order_id.state in QUOTATION_STATES and not self.display_type

    def _apex_logging_active(self):
        ctx = self.env.context
        return not ctx.get('apex_no_line_log') and not ctx.get('install_mode')

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        if lines._apex_logging_active():
            log = self.env['apex.quotation.log']
            for line in lines:
                if line._apex_is_loggable():
                    log._log_line(line, 'line_add')
        return lines

    def write(self, vals):
        if not self._apex_logging_active():
            return super().write(vals)
        log = self.env['apex.quotation.log']
        fnames = [f for f in LINE_WATCHED_FIELDS if f in self._fields]
        tracked = self.filtered(lambda l: l._apex_is_loggable())
        before = {l.id: log._snapshot(l, fnames) for l in tracked}
        res = super().write(vals)
        for line in tracked.exists():
            after = log._snapshot(line, fnames)
            diffs = []
            for fname in fnames:
                old, new = before[line.id].get(fname, ''), after.get(fname, '')
                if old != new:
                    diffs.append("%s: %s -> %s" % (self._fields[fname].string, old or '-', new or '-'))
            if diffs:
                log._log_line(line, 'line_update', changes='\n'.join(diffs))
        return res

    def unlink(self):
        if self._apex_logging_active():
            log = self.env['apex.quotation.log']
            reason = self.env.context.get('apex_lost_reason')
            for line in self:
                if line._apex_is_loggable():
                    log._log_line(line, 'line_delete', reason=reason)
        return super().unlink()

    def action_apex_remove_line(self):
        """Replacement of the trash icon: ask for the reason before removing a product."""
        self.ensure_one()
        if self.order_id.state not in QUOTATION_STATES:
            from odoo.exceptions import UserError
            raise UserError(_("Products can only be removed while the order is a quotation."))
        if self.display_type:  # section / note: no reason needed
            self.unlink()
            return {'type': 'ir.actions.client', 'tag': 'soft_reload'}
        return {
            'type': 'ir.actions.act_window',
            'name': _("Remove Product"),
            'res_model': 'apex.quotation.remove.line',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_line_id': self.id},
        }
