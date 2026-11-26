from lxml import etree

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError

TODO = 'mail.mail_activity_data_todo'

# business fields that cannot be changed while the order is locked
LOCKED_FIELDS = {
    'partner_id', 'partner_ref', 'currency_id', 'date_order', 'date_planned',
    'payment_term_id', 'fiscal_position_id', 'picking_type_id', 'notes', 'origin',
    'user_id', 'incoterm_id', 'incoterm_location', 'order_line', 'dest_address_id',
    'company_id', 'priority', 'receipt_reminder_email', 'reminder_date_before_receipt',
}
# fields that stay editable in the form (our own approval information)
FORM_SKIP_READONLY = {
    'approval_state', 'approval_line_ids', 'approver_ids', 'approval_mode',
    'submitted_by_id', 'rejected_by_id', 'rejection_reason', 'oscon_locked',
    'oscon_status', 'can_approve', 'can_submit', 'can_reset_approval',
}


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    approval_state = fields.Selection(
        [('draft', 'Not Submitted'),
         ('submitted', 'Waiting Approval'),
         ('approved', 'Approved'),
         ('rejected', 'Rejected')],
        string='Approval Status', default='draft', copy=False,
        tracking=True, readonly=True)
    approver_ids = fields.Many2many(
        related='company_id.oscon_po_approver_ids', string='Approvers',
        readonly=True)
    approval_mode = fields.Selection(
        [('all', 'All approvers must approve'),
         ('any', 'Any one approver is enough')],
        string='Approval Rule', copy=False, readonly=True)
    approval_line_ids = fields.One2many(
        'purchase.order.approval.line', 'order_id',
        string='Approvals', copy=False, readonly=True)
    submitted_by_id = fields.Many2one(
        'res.users', string='Submitted By', copy=False, readonly=True)
    rejection_reason = fields.Text(
        string='Rejection Reason', copy=False, readonly=True, tracking=True)
    rejected_by_id = fields.Many2one(
        'res.users', string='Rejected By', copy=False, readonly=True)
    can_approve = fields.Boolean(compute='_compute_can_approve')
    can_submit = fields.Boolean(compute='_compute_can_submit')
    can_reset_approval = fields.Boolean(compute='_compute_can_reset_approval')
    oscon_locked = fields.Boolean(compute='_compute_oscon_locked')
    oscon_status = fields.Selection(
        [('draft', 'RFQ'),
         ('sent', 'RFQ Sent'),
         ('submitted', 'Waiting Approval'),
         ('approved', 'Approved'),
         ('rejected', 'Rejected'),
         ('to approve', 'To Approve'),
         ('purchase', 'Purchase Order'),
         ('done', 'Locked'),
         ('cancel', 'Cancelled')],
        string='Status', compute='_compute_oscon_status', store=True)

    @api.depends('approval_state', 'approval_line_ids.state',
                 'approval_line_ids.user_id')
    def _compute_can_approve(self):
        for order in self:
            order.can_approve = order.approval_state == 'submitted' and any(
                l.user_id == self.env.user and l.state == 'pending'
                for l in order.approval_line_ids)

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == 'form':
            # keep a single status bar: ours (oscon_status), hide Odoo's original one(s)
            # (any statusbar of the main form that is not ours, wherever it sits)
            for node in arch.xpath(
                "//field[@widget='statusbar'][@name!='oscon_status'][not(ancestor::field)]"
            ):
                node.set('invisible', '1')
            # lock every field of the form while the order is locked
            for node in arch.xpath("//sheet//field[not(ancestor::field)]"):
                if node.get('name') in FORM_SKIP_READONLY:
                    continue
                ro = (node.get('readonly') or '').strip()
                if ro in ('1', 'True', 'true'):
                    continue
                node.set('readonly', 'oscon_locked' if ro in ('', '0', 'False', 'false')
                         else '(%s) or oscon_locked' % ro)
        elif view_type == 'list':
            # show the approval-aware status (Waiting Approval / Approved / Rejected / ...)
            for node in arch.xpath("//field[@name='state'][not(ancestor::field)]"):
                new = etree.Element('field', {
                    'name': 'oscon_status',
                    'widget': 'badge',
                    'optional': 'show',
                    'decoration-info': "oscon_status in ('draft', 'sent')",
                    'decoration-warning': "oscon_status in ('submitted', 'to approve')",
                    'decoration-danger': "oscon_status == 'rejected'",
                    'decoration-success': "oscon_status in ('approved', 'purchase', 'done')",
                    'decoration-muted': "oscon_status == 'cancel'",
                })
                node.addnext(new)
                # keep the original field in the view (other expressions may use it) but hide it
                node.set('column_invisible', '1')
                node.attrib.pop('optional', None)
        return arch, view

    def _oscon_is_locked(self):
        """An order is locked once it is submitted/approved (for everybody), and
        after a rejection for everybody except the person who submitted it."""
        self.ensure_one()
        if self.state not in ('draft', 'sent'):
            return False
        if self.approval_state in ('submitted', 'approved'):
            return True
        if (self.approval_state == 'rejected' and self.submitted_by_id
                and self.submitted_by_id != self.env.user):
            return True
        return False

    @api.depends('state', 'approval_state', 'submitted_by_id')
    @api.depends_context('uid')
    def _compute_oscon_locked(self):
        for order in self:
            order.oscon_locked = order._oscon_is_locked()

    @api.depends('state', 'approval_state', 'submitted_by_id')
    @api.depends_context('uid')
    def _compute_can_reset_approval(self):
        for order in self:
            order.can_reset_approval = (
                order.state in ('draft', 'sent')
                and order.approval_state in ('submitted', 'approved')
                and order.submitted_by_id == self.env.user)

    def write(self, vals):
        if (LOCKED_FIELDS & set(vals) and not self.env.su
                and not self.env.context.get('oscon_bypass_lock')):
            for order in self:
                if order._oscon_is_locked():
                    raise UserError(_(
                        'Order %s is locked because it was submitted for approval. '
                        'Use "Set to Draft" first if you need to change it.', order.name))
        return super().write(vals)

    def action_reset_approval(self):
        for order in self:
            if not order.can_reset_approval:
                raise UserError(_('Only the person who submitted this order can set it back to draft.'))
            approvers = order.approval_line_ids.user_id
            order._clear_approver_activities()
            order.approval_line_ids.unlink()
            order.write({
                'approval_state': 'draft',
                'submitted_by_id': False,
                'rejection_reason': False,
                'rejected_by_id': False,
            })
            order.message_post(
                body=_('%s set the order back to draft. It must be submitted for approval again.',
                       self.env.user.name),
                partner_ids=approvers.partner_id.ids,
                subtype_xmlid='mail.mt_comment')
        return True

    @api.depends('state', 'approval_state')
    def _compute_oscon_status(self):
        for order in self:
            if order.state in ('draft', 'sent') and order.approval_state != 'draft':
                order.oscon_status = order.approval_state
            else:
                order.oscon_status = order.state

    @api.depends('state', 'approval_state', 'submitted_by_id')
    @api.depends_context('uid')
    def _compute_can_submit(self):
        for order in self:
            if order.state not in ('draft', 'sent'):
                order.can_submit = False
            elif order.approval_state == 'draft':
                order.can_submit = True
            elif order.approval_state == 'rejected':
                # only the person who submitted may fix and re-submit
                order.can_submit = (
                    not order.submitted_by_id
                    or order.submitted_by_id == self.env.user)
            else:
                order.can_submit = False

    # ------------------------------------------------------------------
    # Submit
    # ------------------------------------------------------------------
    def action_submit_for_approval(self):
        for order in self:
            if order.state not in ('draft', 'sent'):
                raise UserError(_('Only RFQs can be submitted for approval.'))
            if order.approval_state in ('submitted', 'approved'):
                raise UserError(_('This order is already submitted or approved.'))
            if (order.approval_state == 'rejected' and order.submitted_by_id
                    and self.env.user != order.submitted_by_id
                    and not self.env.is_superuser()):
                raise UserError(_(
                    'Only %s, who submitted this order, can fix it and submit it again.',
                    order.submitted_by_id.name))
            if not order.order_line:
                raise UserError(_('Please add at least one product line before submitting.'))
            company = order.company_id
            approvers = company.oscon_po_approver_ids
            if not approvers:
                raise UserError(_(
                    'No approvers are configured. Please ask a Purchase Manager to add them in '
                    'Purchase > Configuration > Settings > Approvals.'))

            order.approval_line_ids.unlink()
            order.write({
                'approval_line_ids': [Command.create({'user_id': u.id})
                                      for u in approvers],
                'approval_mode': company.oscon_po_approval_mode,
                'approval_state': 'submitted',
                'submitted_by_id': self.env.uid,
                'rejection_reason': False,
                'rejected_by_id': False,
            })
            for user in approvers:
                order.activity_schedule(
                    TODO, user_id=user.id,
                    summary=_('Approve Purchase Order %s', order.name),
                    note=_('%(user)s submitted this purchase order for your approval.',
                           user=self.env.user.name))
            order.message_post(
                body=_('Submitted for approval to: %s', ', '.join(approvers.mapped('name'))),
                partner_ids=approvers.partner_id.ids,
                subtype_xmlid='mail.mt_comment')
        return True

    # ------------------------------------------------------------------
    # Approve / Reject
    # ------------------------------------------------------------------
    def _get_my_pending_line(self):
        self.ensure_one()
        line = self.approval_line_ids.filtered(
            lambda l: l.user_id == self.env.user and l.state == 'pending')
        if self.approval_state != 'submitted' or not line:
            raise UserError(_('You are not allowed to approve/reject this order now.'))
        return line[:1]

    def _clear_approver_activities(self):
        self.ensure_one()
        self.activity_ids.filtered(
            lambda a: a.user_id in self.approval_line_ids.user_id).unlink()

    def _notify_submitter(self, body):
        self.ensure_one()
        self.message_post(
            body=body, partner_ids=self.submitted_by_id.partner_id.ids,
            subtype_xmlid='mail.mt_comment')
        if self.submitted_by_id:
            self.activity_schedule(
                TODO, user_id=self.submitted_by_id.id,
                summary=_('Purchase Order %s: approval update', self.name),
                note=body)

    def action_approve(self):
        for order in self:
            line = order._get_my_pending_line()
            line.sudo().write({'state': 'approved', 'date': fields.Datetime.now()})
            order.activity_feedback([TODO], user_id=self.env.uid)
            lines = order.approval_line_ids
            if order.approval_mode == 'any':
                done = any(l.state == 'approved' for l in lines)
            else:
                done = all(l.state == 'approved' for l in lines)
            if done:
                order.write({'approval_state': 'approved'})
                order._clear_approver_activities()
                order._notify_submitter(
                    _('Purchase order approved. You can now confirm the order.'))
            else:
                order.message_post(body=_('%s approved this order.', self.env.user.name))
        return True

    def action_reject(self):
        self.ensure_one()
        self._get_my_pending_line()
        return {
            'name': _('Reject Purchase Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_order_id': self.id},
        }

    def _do_reject(self, reason):
        for order in self:
            line = order._get_my_pending_line()
            line.sudo().write({
                'state': 'rejected',
                'date': fields.Datetime.now(),
                'note': reason,
            })
            order.write({
                'approval_state': 'rejected',
                'rejection_reason': reason,
                'rejected_by_id': self.env.uid,
            })
            order._clear_approver_activities()
            order._notify_submitter(
                _('Purchase order rejected by %(user)s. Reason: %(reason)s',
                  user=self.env.user.name, reason=reason))

    # ------------------------------------------------------------------
    # Enforcement & reset
    # ------------------------------------------------------------------
    def button_confirm(self):
        for order in self:
            if order.state not in ('draft', 'sent'):
                continue
            if order.approval_state != 'approved':
                raise UserError(_(
                    'Purchase order %s must be approved before it can be confirmed. '
                    'Please use "Submit for Approval".', order.name))
            if (not self.env.is_superuser()
                    and order.submitted_by_id
                    and self.env.user != order.submitted_by_id):
                raise UserError(_(
                    'You are not allowed to confirm this order.\n'
                    'Only %(submitter)s, who submitted it for approval, can confirm it. '
                    'Approvers can only Approve or Reject.',
                    submitter=order.submitted_by_id.name))
        return super(PurchaseOrder, self.with_context(oscon_bypass_lock=True)).button_confirm()

    def button_draft(self):
        res = super().button_draft()
        self.approval_line_ids.unlink()
        self.write({
            'approval_state': 'draft',
            'rejection_reason': False,
            'rejected_by_id': False,
            'submitted_by_id': False,
        })
        return res
