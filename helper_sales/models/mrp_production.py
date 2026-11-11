# -*- coding: utf-8 -*-

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare

PROD_GROUP = 'helper_sales.group_mo_production_manager'
COST_GROUP = 'helper_sales.group_mo_cost_share_manager'
ACTIVITY_SUMMARY = 'Manufacturing Approval'


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    approval_state = fields.Selection(
        [
            ('draft', 'Not Submitted'),
            ('prod_pending', 'Waiting Production Manager'),
            ('rejected', 'Rejected'),
            ('prod_approved', 'Production Approved'),
            ('cost_pending', 'Waiting Cost Shared Manager'),
            ('cost_approved', 'Cost Shared Approved'),
            ('backorder_pending', 'Waiting Production Manager (Backorder)'),
        ],
        string='Approval Status', default='draft', copy=False, tracking=True,
    )
    reject_reason = fields.Text(string='Rejection Reason', copy=False, readonly=True)
    prod_approved_by = fields.Many2one('res.users', string='Production Approved By', copy=False, readonly=True)
    prod_approved_date = fields.Datetime(string='Production Approved On', copy=False, readonly=True)
    cost_approved_by = fields.Many2one('res.users', string='Cost Shared Approved By', copy=False, readonly=True)
    cost_approved_date = fields.Datetime(string='Cost Shared Approved On', copy=False, readonly=True)

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _users_in_group(self, xmlid):
        group = self.env.ref(xmlid)
        return self.env['res.users'].sudo().search([('groups_id', 'in', group.id), ('share', '=', False)])

    def _ensure_approvers_exist(self, xmlid, label):
        if not self._users_in_group(xmlid):
            raise UserError(_(
                "No user is set as %s. Please ask the Administrator to add a user to the group "
                "'%s' (Settings > Users).", label, self.env.ref(xmlid).name))

    def _schedule_approval_activity(self, xmlid, note):
        users = self._users_in_group(xmlid)
        for production in self:
            for user in users:
                try:
                    production.activity_schedule(
                        'mail.mail_activity_data_todo', summary=ACTIVITY_SUMMARY, note=note, user_id=user.id)
                except UserError:
                    continue

    def _close_approval_activities(self):
        self.sudo().activity_ids.filtered(lambda a: a.summary == ACTIVITY_SUMMARY)._action_done()

    def _notify_creator(self, body):
        for production in self:
            production.message_post(
                body=body,
                partner_ids=production.create_uid.partner_id.ids,
                subtype_xmlid='mail.mt_comment',
            )

    @staticmethod
    def _notification(title, message, notif_type='info'):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'type': notif_type,
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }

    # ------------------------------------------------------------------
    # Level 1: Production Manager
    # ------------------------------------------------------------------
    def action_submit_for_approval(self):
        for production in self:
            if production.state != 'draft':
                raise UserError(_("Only draft Manufacturing Orders can be submitted for approval."))
        self._ensure_approvers_exist(PROD_GROUP, _("Production Manager"))
        to_submit = self.filtered(lambda p: p.approval_state in ('draft', 'rejected'))
        to_submit.write({'approval_state': 'prod_pending', 'reject_reason': False})
        for production in to_submit:
            production.message_post(body=_("Submitted for Production Manager approval by %s.", self.env.user.name))
        to_submit._schedule_approval_activity(
            PROD_GROUP, _("Please review this Manufacturing Order and Approve or Reject it."))
        return True

    def action_approve_production(self):
        if not self.env.user.has_group(PROD_GROUP):
            raise UserError(_("Only a Production Manager can approve this Manufacturing Order."))
        for production in self:
            if production.state != 'draft' or production.approval_state != 'prod_pending':
                raise UserError(_("%s is not waiting for Production Manager approval.", production.name))
        self.write({
            'approval_state': 'prod_approved',
            'prod_approved_by': self.env.uid,
            'prod_approved_date': fields.Datetime.now(),
            'reject_reason': False,
        })
        self._close_approval_activities()
        self.action_confirm()  # approved => automatically confirmed
        self._notify_creator(_("Approved by Production Manager %s. You can continue with Produce All.", self.env.user.name))
        return True

    # ------------------------------------------------------------------
    # Rejection (both levels) - the reason is asked in a pop-up
    # ------------------------------------------------------------------
    def action_open_reject_wizard(self):
        self.ensure_one()
        level = 'cost' if self.approval_state == 'cost_pending' else 'production'
        return {
            'type': 'ir.actions.act_window',
            'name': _("Reject Manufacturing Order"),
            'res_model': 'mrp.production.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_production_id': self.id, 'default_level': level},
        }

    def _do_reject(self, level, reason):
        group = PROD_GROUP if level == 'production' else COST_GROUP
        label = _("Production Manager") if level == 'production' else _("Cost Shared Manager")
        expected = 'prod_pending' if level == 'production' else 'cost_pending'
        if not self.env.user.has_group(group):
            raise UserError(_("Only the %s can reject this Manufacturing Order.", label))
        for production in self:
            if production.approval_state != expected:
                raise UserError(_("%s is not waiting for %s approval.", production.name, label))
        # Level 1 rejection -> back to draft (resubmit); Level 2 rejection -> back to the creator
        self.write({
            'approval_state': 'rejected' if level == 'production' else 'prod_approved',
            'reject_reason': reason,
        })
        self._close_approval_activities()
        self._notify_creator(_("Rejected by %s (%s). Reason: %s", self.env.user.name, label, reason))

    # ------------------------------------------------------------------
    # Level 2: Cost Shared Manager
    # ------------------------------------------------------------------
    def action_wait_cost_approval(self):
        return self._notification(
            _("Waiting for Cost Shared Approval"),
            _("This Manufacturing Order is waiting for the Cost Shared Manager. "
              "You will be notified once it is approved."),
            'warning',
        )

    def _send_for_cost_approval(self):
        self._ensure_approvers_exist(COST_GROUP, _("Cost Shared Manager"))
        self.write({'approval_state': 'cost_pending', 'reject_reason': False})
        for production in self:
            production.message_post(body=_("Sent for Cost Shared Manager approval by %s.", self.env.user.name))
        self._schedule_approval_activity(
            COST_GROUP, _("Please review the Cost Share (%) and click Produce All to approve, or Reject."))

    def _approve_cost_share(self):
        self.write({
            'approval_state': 'cost_approved',
            'cost_approved_by': self.env.uid,
            'cost_approved_date': fields.Datetime.now(),
            'reject_reason': False,
        })
        self._close_approval_activities()
        for production in self:
            production.message_post(body=_("Cost Shared approved by %s.", self.env.user.name))

    # ------------------------------------------------------------------
    # Backorder decision belongs to the Production Manager
    # ------------------------------------------------------------------
    def action_wait_backorder_decision(self):
        return self._notification(
            _("Waiting for Production Manager"),
            _("The Production Manager must decide 'Create Backorder' or 'No Backorder' to finish this order."),
            'warning',
        )

    def _is_partial_production(self):
        """ True when only part of the quantity is produced (Odoo would ask for a Backorder). """
        self.ensure_one()
        rounding = self.product_uom_id.rounding
        return (float_compare(self.qty_producing, 0, precision_rounding=rounding) > 0
                and float_compare(self.qty_producing, self.product_qty, precision_rounding=rounding) < 0)

    def _hand_over_to_production_manager(self):
        self._ensure_approvers_exist(PROD_GROUP, _("Production Manager"))
        to_hand_over = self.filtered(lambda p: p.approval_state != 'backorder_pending')
        if to_hand_over:
            to_hand_over.write({'approval_state': 'backorder_pending'})
            to_hand_over._close_approval_activities()
            for production in to_hand_over:
                production.message_post(body=_(
                    "Cost Shared approved. Only part of the quantity is produced, so the Production Manager "
                    "must decide Backorder / No Backorder."))
            to_hand_over._schedule_approval_activity(
                PROD_GROUP, _("Cost Shared approved. Please click Produce All / Mark as Done and decide "
                              "Create Backorder or No Backorder."))

    # ------------------------------------------------------------------
    # Checks used by Produce All / Mark as Done
    # ------------------------------------------------------------------
    def _get_approval_stage(self):
        """ MOs confirmed outside the approval flow (e.g. created by the scheduler or
        confirmed before this module) are treated as already production-approved. """
        self.ensure_one()
        if self.approval_state in ('draft', 'rejected') and self.state not in ('draft', 'cancel'):
            return 'prod_approved'
        return self.approval_state

    def _check_is_creator(self):
        self.ensure_one()
        allowed = self.create_uid | self.user_id
        if self.env.user not in allowed:
            raise UserError(_(
                "Only the person who created this Manufacturing Order (%s) can continue with Produce All.",
                self.create_uid.name))

    def _check_ready_to_produce(self):
        """ Transfer done + component Quantity filled + Cost Share filled. """
        self.ensure_one()
        errors = []

        pickings = self.picking_ids.filtered(lambda p: p.state != 'cancel')
        pending = pickings.filtered(lambda p: p.state != 'done')
        if pending:
            errors.append(_("The Transfer must be completed first: %s", ', '.join(pending.mapped('name'))))

        raw_moves = self.move_raw_ids.filtered(lambda m: m.state != 'cancel' and m.product_uom_qty > 0)
        empty = raw_moves.filtered(lambda m: m.quantity <= 0)
        if empty:
            errors.append(_(
                "The Quantity in the Components tab must be filled for: %s",
                ', '.join(empty.mapped('product_id.display_name'))))

        byproducts = self.move_byproduct_ids.filtered(lambda m: m.state != 'cancel')
        no_share = byproducts.filtered(lambda m: not m.cost_share)
        if no_share:
            errors.append(_(
                "The Cost Share (%%) in the By-Products tab must be filled for: %s",
                ', '.join(no_share.mapped('product_id.display_name'))))

        if errors:
            raise UserError(
                _("You cannot Produce yet. Please do the following:") + "\n\n- " + "\n- ".join(errors))

    # ------------------------------------------------------------------
    # Overrides
    # ------------------------------------------------------------------
    def action_confirm(self):
        res = super().action_confirm()
        # Confirmed without going through the approval (scheduler / procurement): mark as production-approved
        self.filtered(lambda p: p.approval_state in ('draft', 'rejected')).write({'approval_state': 'prod_approved'})
        return res

    def write(self, vals):
        if vals.get('state') == 'draft' and 'approval_state' not in vals:
            vals = dict(vals, approval_state='draft', reject_reason=False)
        return super().write(vals)

    def button_mark_done(self):
        """ Produce All / Mark as Done """
        if self.env.su or self.env.context.get('skip_mo_approval_check'):
            return super().button_mark_done()

        to_cost_approval = self.env['mrp.production']
        for production in self:
            stage = production._get_approval_stage()
            if stage in ('cost_approved', 'backorder_pending'):
                continue
            if production.state == 'draft':
                if stage == 'prod_pending':
                    raise UserError(_("%s is waiting for the Production Manager's approval.", production.name))
                raise UserError(_("%s must be approved first. Please click 'Submit for Approval'.", production.name))
            if stage == 'cost_pending':
                if self.env.user.has_group(COST_GROUP):
                    production._approve_cost_share()  # final approval, the flow continues below
                    continue
                raise UserError(_("%s is waiting for the Cost Shared Manager's approval.", production.name))
            # stage == 'prod_approved': the creator continues
            production._check_is_creator()
            production._check_ready_to_produce()
            to_cost_approval |= production

        if to_cost_approval:
            to_cost_approval._send_for_cost_approval()
            remaining = self - to_cost_approval
            if not remaining:
                return self._notification(
                    _("Sent for Cost Shared Approval"),
                    _("Everything is ready. The Cost Shared Manager must approve before you can Produce All."),
                    'success',
                )
            self = remaining

        # Partial production => the Production Manager decides Backorder / No Backorder
        if not self.env.user.has_group(PROD_GROUP):
            partial = self.filtered(lambda p: p._is_partial_production())
            if partial:
                partial._hand_over_to_production_manager()
                remaining = self - partial
                if not remaining:
                    return self._notification(
                        _("Sent to Production Manager"),
                        _("Cost Shared is approved. The Production Manager will decide Backorder / No Backorder "
                          "and finish this order."),
                        'success',
                    )
                self = remaining
        else:
            self.filtered(lambda p: p.approval_state == 'backorder_pending')._close_approval_activities()

        return super(MrpProduction, self).button_mark_done()
