from odoo import api, fields, models
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    approved_by = fields.Many2one(
        'res.users',
        string='Approved By',
        readonly=True,
        copy=False,
        tracking=True,
    )

    approved_date = fields.Datetime(
        string='Approved Date',
        readonly=True,
        copy=False,
        tracking=True,
    )

    approval_submitted_by = fields.Many2one(
        'res.users',
        string='Submitted For Approval By',
        readonly=True,
        copy=False,
        tracking=True,
    )

    reject_reason = fields.Text(
        string='Reason for Rejection',
        readonly=True,
        copy=False,
        tracking=True,
    )

    # ==========================================================
    # APPROVAL ENABLED
    # ==========================================================

    approval_enabled = fields.Boolean(
        string='Approval Enabled',
        compute='_compute_approval_enabled',
    )

    @api.depends(
        'company_id',
        'company_id.purchase_approval_required',
    )
    def _compute_approval_enabled(self):
        for order in self:
            order.approval_enabled = bool(
                order.company_id.purchase_approval_required
            )

    approval_stage = fields.Selection(
        selection=[
            ('none', 'None'),
            (
                'waiting_procurement',
                'Wait for Procurement Approval'
            ),
            (
                'procurement_approved',
                'Procurement Manager Approved'
            ),
            (
                'finance_approved',
                'Finance Manager Approved'
            ),
            (
                'rejected',
                'Rejected'
            ),
            (
                'purchase',
                'Purchase Order'
            ),
        ],
        string='Approval Stage',
        default='none',
        copy=False,
        tracking=True,
    )

    can_approve_procurement = fields.Boolean(
        string='Can Approve Procurement',
        compute='_compute_can_approve_procurement',
    )

    @api.depends(
        'state',
        'approval_stage',
        'company_id',
        'company_id.purchase_approval_required',
        'company_id.procurement_manager_id',
    )
    def _compute_can_approve_procurement(self):
        current_user = self.env.user

        for order in self:
            order.can_approve_procurement = bool(
                order.state == 'waiting_approval'
                and order.approval_stage == 'waiting_procurement'
                and order.company_id.purchase_approval_required
                and order.company_id.procurement_manager_id == current_user
            )

    # ==========================================================
    # FINANCE MANAGER
    # ==========================================================

    can_approve_finance = fields.Boolean(
        string='Can Approve Finance',
        compute='_compute_can_approve_finance',
    )

    @api.depends(
        'state',
        'approval_stage',
        'company_id',
        'company_id.purchase_approval_required',
        'company_id.finance_manager_id',
    )
    def _compute_can_approve_finance(self):
        current_user = self.env.user

        for order in self:
            order.can_approve_finance = bool(
                order.state == 'procurement_approved'
                and order.approval_stage == 'procurement_approved'
                and order.company_id.purchase_approval_required
                and order.company_id.finance_manager_id == current_user
            )

    can_reject_or_cancel = fields.Boolean(
        string='Can Reject Or Cancel',
        compute='_compute_can_reject_or_cancel',
    )

    @api.depends(
        'approval_stage',
        'company_id.procurement_manager_id',
        'company_id.finance_manager_id',
    )
    def _compute_can_reject_or_cancel(self):
        current_user = self.env.user
        for order in self:
            is_proc = order.company_id.procurement_manager_id == current_user
            is_fin = order.company_id.finance_manager_id == current_user
            
            if order.approval_stage == 'waiting_procurement':
                order.can_reject_or_cancel = is_proc
            elif order.approval_stage == 'procurement_approved':
                order.can_reject_or_cancel = is_proc or is_fin
            elif order.approval_stage == 'finance_approved':
                order.can_reject_or_cancel = is_fin
            else:
                order.can_reject_or_cancel = False

    can_confirm_purchase = fields.Boolean(
        string='Can Confirm Purchase',
        compute='_compute_can_confirm_purchase',
    )

    @api.depends(
        'state',
        'approval_stage',
        'approval_submitted_by',
        'company_id',
        'company_id.purchase_approval_required',
    )
    def _compute_can_confirm_purchase(self):
        current_user = self.env.user

        for order in self:
            order.can_confirm_purchase = bool(
                order.company_id.purchase_approval_required
                and order.approval_stage == 'finance_approved'
                and order.approval_submitted_by == current_user
            )

    state = fields.Selection(
        selection_add=[
            ('waiting_approval', 'Wait for Approval'),
            ('procurement_approved', 'Procurement Approved'),
            ('finance_approved', 'Finance Approved'),
            ('rejected', 'Rejected'),
        ],
        ondelete={
            'waiting_approval': 'set default',
            'procurement_approved': 'set default',
            'finance_approved': 'set default',
            'rejected': 'set default',
        },
    )

    approval_statusbar = fields.Selection(
        selection=[
            ('draft', 'RFQ'),
            (
                'waiting_approval',
                'Wait for Procurement Approval'
            ),
            (
                'procurement_approved',
                'Procurement Manager Approved'
            ),
            (
                'finance_approved',
                'Finance Manager Approved'
            ),
            (
                'rejected',
                'Rejected'
            ),
            (
                'purchase',
                'Purchase Order'
            ),
            (
                'done',
                'Locked'
            ),
            (
                'cancel',
                'Cancelled'
            ),
        ],
        string='Approval Workflow',
        compute='_compute_approval_statusbar',
        readonly=True,
    )

    @api.depends(
        'state',
        'approval_stage',
        'approval_enabled',
    )
    def _compute_approval_statusbar(self):
        for order in self:
            if not order.approval_enabled:
                order.approval_statusbar = order.state
                continue

            if order.state in ('purchase', 'done', 'cancel'):
                order.approval_statusbar = order.state
                continue

            if order.approval_stage == 'rejected' or order.state == 'rejected':
                order.approval_statusbar = 'rejected'
                continue

            if order.approval_stage == 'waiting_procurement':
                order.approval_statusbar = 'waiting_approval'
                continue

            if order.approval_stage == 'procurement_approved':
                order.approval_statusbar = 'procurement_approved'
                continue

            if order.approval_stage == 'finance_approved':
                order.approval_statusbar = 'finance_approved'
                continue

            order.approval_statusbar = order.state

    def action_submit_for_approval(self):
        for order in self:
            if not order.company_id.purchase_approval_required:
                raise UserError(
                    "Purchase Approval is not enabled for this company."
                )

            if (
                not order.company_id.procurement_manager_id
                or not order.company_id.finance_manager_id
            ):
                raise UserError(
                    "Both Procurement Manager and Finance Manager "
                    "must be assigned in Company Settings."
                )

            if order.state != 'draft':
                raise UserError(
                    "Only a draft RFQ can be submitted for approval."
                )

            if order.approval_stage not in ('none', 'rejected'):
                raise UserError(
                    "This purchase order has already been submitted "
                    "or processed through the approval workflow."
                )

            # --- UKAGUZI WA ATTACHMENT WAMEHAMISHIA HAPA (SUBMIT FOR APPROVAL) ---
            attachment_count = self.env['ir.attachment'].search_count([
                ('res_model', '=', 'purchase.order'),
                ('res_id', '=', order.id)
            ])
            
            # Angalia pia kwenye mail.message kama kuna attachments za chatter
            if attachment_count == 0:
                msg_attachments = self.env['ir.attachment'].search_count([
                    ('res_model', '=', 'mail.message'),
                    ('res_id', 'in', order.message_ids.ids)
                ])
                attachment_count += msg_attachments

            if attachment_count == 0:
                raise UserError(
                    f"You cannot submit purchase order ({order.name}) for approval! Please attach the required document in the attachment section below first."
                )

            order.write({
                'state': 'waiting_approval',
                'approval_stage': 'waiting_procurement',
                'approval_submitted_by': self.env.user.id,
                'approved_by': False,
                'approved_date': False,
                'reject_reason': False,
            })
            order.modified(['state', 'approval_stage', 'approval_statusbar'])

            # --- TUMA ACTIVITY NOTIFICATION KWA PROCUREMENT MANAGER ---
            if order.company_id.procurement_manager_id:
                order.activity_feedback(['mail.mail_activity_data_todo'])
                
                order.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=order.company_id.procurement_manager_id.id,
                    summary='Pending Purchase Approval',
                    note=f'Please review and approve purchase order {order.name} submitted by {self.env.user.name}.'
                )

        return True

    def action_set_to_draft_custom(self):
        for order in self:
            order.write({
                'state': 'draft',
                'approval_stage': 'none',
            })
            order.modified(['state', 'approval_stage', 'approval_statusbar'])
        return True

    def action_approve_procurement(self):
        for order in self:
            if not order.can_approve_procurement:
                raise UserError(
                    "You are not authorized to give Procurement approval."
                )

            order.write({
                'state': 'procurement_approved',
                'approval_stage': 'procurement_approved',
            })
            order.modified(['state', 'approval_stage', 'approval_statusbar'])

            # --- MALIZA ACTIVITY YA PROCUREMENT NA TUMA KWA FINANCE MANAGER ---
            order.activity_feedback(['mail.mail_activity_data_todo'])

            if order.company_id.finance_manager_id:
                order.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=order.company_id.finance_manager_id.id,
                    summary='Pending Finance Approval',
                    note=f'Procurement approved purchase order {order.name}. Your financial approval is required.'
                )

        return True

    def action_approve_finance(self):
        for order in self:
            if not order.can_approve_finance:
                raise UserError(
                    "You are not authorized to give Finance approval."
                )

            order.write({
                'state': 'draft',
                'approval_stage': 'finance_approved',
                'approved_by': self.env.user.id,
                'approved_date': fields.Datetime.now(),
            })
            order.modified(['state', 'approval_stage', 'approval_statusbar'])

            # --- MALIZA ACTIVITY YA FINANCE NA TUMA KWA USER ALIYE-SUBMIT A-CONFIRM ---
            order.activity_feedback(['mail.mail_activity_data_todo'])

            if order.approval_submitted_by:
                order.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=order.approval_submitted_by.id,
                    summary='Confirm Purchase Order',
                    note=f'Purchase order {order.name} has been fully approved. Please confirm the order.'
                )

        return True

    def action_reject(self):
        self.ensure_one()

        if not self.can_reject_or_cancel:
            raise UserError(
                "You are not authorized to reject this order."
            )

        return {
            'name': 'Reason for Rejection',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_order_id': self.id,
            },
        }

    def button_cancel(self):
        for order in self:
            if not order.can_reject_or_cancel:
                raise UserError(
                    "You are not authorized to cancel this order."
                )
            order.write({
                'state': 'cancel',
                'approval_stage': 'rejected',
            })
            order.modified(['state', 'approval_stage', 'approval_statusbar'])
            
            order.activity_feedback(['mail.mail_activity_data_todo'])

        return True

    def button_confirm(self):
        for order in self:
            if order.company_id.purchase_approval_required:
                if order.approval_stage != 'finance_approved':
                    raise UserError(
                        "This order must be fully approved by "
                        "both Procurement and Finance before confirmation."
                    )

                if order.approval_submitted_by != self.env.user:
                    raise UserError(
                        "Only the user who submitted this "
                        "purchase order for approval can confirm it."
                    )
                # (Ukaguzi wa attachment umeondolewa hapa kwenye confirm na kuhamishiwa kwenye Submit for Approval)

        res = super().button_confirm()

        for order in self:
            if order.company_id.purchase_approval_required:
                order.write({
                    'state': 'purchase',
                    'approval_stage': 'purchase',
                })
                order.modified(['state', 'approval_stage', 'approval_statusbar'])
                
                order.activity_feedback(['mail.mail_activity_data_todo'])

        return res


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    qty_available = fields.Float(
        string='On Hand',
        related='product_id.qty_available',
        readonly=True,
        digits='Product Unit of Measure',
    )

    product_qty = fields.Float(
        readonly=True,
        states={
            'draft': [('readonly', False)],
        },
    )