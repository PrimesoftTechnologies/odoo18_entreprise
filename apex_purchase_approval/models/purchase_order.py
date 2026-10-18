from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError

TODO = 'mail.mail_activity_data_todo'


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # Same keys as standard Odoo; only the label of 'to approve' changed.
    state = fields.Selection(
        selection=[
            ('draft', 'RFQ'),
            ('sent', 'RFQ Sent'),
            ('to approve', 'Wait for Approval'),
            ('purchase', 'Purchase Order'),
            ('done', 'Locked'),
            ('cancel', 'Cancelled'),
        ],
        string='Status', readonly=True, index=True, copy=False,
        default='draft', tracking=True,
    )
    apex_approver_id = fields.Many2one(
        'res.users', string='Approver', tracking=True, copy=False,
        domain=[('share', '=', False)],
        help="User who must approve this order before it becomes a Purchase Order.",
    )
    is_apex_approver = fields.Boolean(compute='_compute_is_apex_approver')

    @api.depends('apex_approver_id')
    @api.depends_context('uid')
    def _compute_is_apex_approver(self):
        for order in self:
            order.is_apex_approver = bool(order.apex_approver_id) and order.apex_approver_id == self.env.user

    # ------------------------------------------------------------------
    # Force every confirmation through the approval step
    # ------------------------------------------------------------------
    def _approval_allowed(self):
        self.ensure_one()
        if self.env.context.get('apex_force_approve'):
            return True
        return False

    def button_confirm(self):
        to_submit = self.filtered(lambda o: o.state in ('draft', 'sent'))
        for order in to_submit:
            if not order.apex_approver_id:
                raise UserError(_("Please select an Approver before confirming order %s.", order.name))
        res = super().button_confirm()
        for order in to_submit.filtered(lambda o: o.state == 'to approve'):
            order._apex_notify_approver()
        return res

    def button_cancel(self):
        waiting = self.filtered(lambda o: o.state == 'to approve' and o.apex_approver_id)
        for order in waiting:
            order.activity_unlink([TODO], user_id=order.apex_approver_id.id)
        return super().button_cancel()

    # ------------------------------------------------------------------
    # Notifications
    # ------------------------------------------------------------------
    def _apex_notify_approver(self):
        for order in self:
            approver = order.apex_approver_id
            partner = approver.partner_id
            amount = order.currency_id.format(order.amount_total)
            order.message_subscribe(partner_ids=partner.ids)
            # 1) Chatter message (Send message area) -> approver is notified
            order.message_post(
                body=Markup(_(
                    "<p>Hello %(approver)s,</p>"
                    "<p>Purchase order <b>%(name)s</b> from <b>%(vendor)s</b> "
                    "(total: <b>%(amount)s</b>) is waiting for your approval.</p>"
                )) % {
                    'approver': approver.name,
                    'name': order.name,
                    'vendor': order.partner_id.display_name or '',
                    'amount': amount,
                },
                subject=_("Approval needed: %s", order.name),
                partner_ids=partner.ids,
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
            )
            # 2) Activity -> shows on the clock icon in the top bar
            order.activity_schedule(
                TODO,
                user_id=approver.id,
                summary=_("Approve Purchase Order %s", order.name),
                note=_("Vendor: %(vendor)s - Total: %(amount)s",
                       vendor=order.partner_id.display_name or '', amount=amount),
            )

    def _apex_notify_buyer(self, body):
        for order in self:
            buyer = order.user_id or order.create_uid
            order.message_post(
                body=body,
                partner_ids=buyer.partner_id.ids,
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
            )

    # ------------------------------------------------------------------
    # Approve / Reject
    # ------------------------------------------------------------------
    def _apex_check_approver(self):
        for order in self:
            if order.state != 'to approve':
                raise UserError(_("Order %s is not waiting for approval.", order.name))
            if order.apex_approver_id != self.env.user:
                raise UserError(_("Only the assigned approver (%s) can do this.", order.apex_approver_id.name))

    def action_apex_approve(self):
        self._apex_check_approver()
        for order in self:
            order.sudo().with_context(apex_force_approve=True).button_approve()
            order.activity_feedback([TODO], user_id=self.env.user.id, feedback=_("Approved"))
            order._apex_notify_buyer(Markup(_(
                "<p>Purchase order <b>%(name)s</b> was <b>approved</b> by %(user)s.</p>"
            )) % {'name': order.name, 'user': self.env.user.name})
        return True

    def action_apex_open_reject(self):
        self.ensure_one()
        self._apex_check_approver()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Reject Order"),
            'res_model': 'apex.purchase.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_order_id': self.id},
        }

    def _apex_reject(self, reason):
        self._apex_check_approver()
        for order in self:
            order.activity_feedback([TODO], user_id=self.env.user.id, feedback=_("Rejected"))
            order.write({'state': 'draft'})
            order._apex_notify_buyer(Markup(_(
                "<p>Purchase order <b>%(name)s</b> was <b>rejected</b> by %(user)s.</p>"
                "<p>Reason: %(reason)s</p>"
            )) % {'name': order.name, 'user': self.env.user.name, 'reason': reason})
