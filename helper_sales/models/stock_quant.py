from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    count_approval_state = fields.Selection(
        [('draft', 'Not Requested'), ('waiting', 'Waiting Approval'), ('approved', 'Approved')],
        string='Count Approval', default='draft', copy=False, readonly=True,
    )
    count_approved_by = fields.Many2one('res.users', string='Count Approved By', copy=False, readonly=True)

    @api.model
    def _get_inventory_fields_write(self):
        return list(super()._get_inventory_fields_write()) + ['count_approval_state', 'count_approved_by']

    def write(self, vals):
        # Changing the counted quantity cancels any earlier approval
        if ('inventory_quantity' in vals and 'count_approval_state' not in vals
                and not self.env.context.get('count_approval_bypass')):
            vals = dict(vals, count_approval_state='draft', count_approved_by=False)
        return super().write(vals)

    def action_request_count_approval(self):
        quants = self.filtered('inventory_quantity_set')
        if not quants:
            raise UserError(_("Please enter the Counted Quantity first."))
        quants.sudo().write({'count_approval_state': 'waiting', 'count_approved_by': False})
        return True

    def action_approve_count(self):
        if not self.env.user.has_group('helper_sales.group_stock_count_approver'):
            raise UserError(_("Only a Physical Count Approver can approve stock counts."))
        quants = self.filtered(lambda q: q.count_approval_state == 'waiting')
        quants.sudo().write({'count_approval_state': 'approved', 'count_approved_by': self.env.user.id})
        return True

    def _check_count_approval(self):
        if self.env.su or self.env.context.get('count_approval_bypass'):
            return
        pending = self.filtered(lambda q: q.inventory_quantity_set and q.count_approval_state != 'approved')
        if pending:
            raise UserError(_(
                "Physical stock counting needs approval.\n"
                "Click 'Request Approval' and wait for an approver before applying.\n\nProducts: %s",
                ', '.join(pending.mapped('product_id.display_name')[:10]),
            ))

    def action_stock_inventory_adjustement_name(self):
        self._check_count_approval()
        return super().action_stock_inventory_adjustement_name()

    def action_apply_inventory(self):
        self._check_count_approval()
        return super().action_apply_inventory()

    def _set_inventory_quantity(self):
        # Direct "On Hand Quantity" edits (Update Quantity) are controlled by the Update Quantity group instead
        return super(StockQuant, self.with_context(count_approval_bypass=True))._set_inventory_quantity()
