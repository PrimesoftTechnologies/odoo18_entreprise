from odoo import fields, models, _, api
from odoo.exceptions import UserError

FINANCE_GROUP = 'bic_approval_request.group_finance_approver'
CEO_GROUP = 'bic_approval_request.group_ceo_approver'


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    state = fields.Selection(
        selection_add=[
            ('finance_approval', 'Finance Approval'),
            ('ceo_approval', 'CEO Approval'),
            ('to approve',),
        ],
        ondelete={
            'finance_approval': 'set default',
            'ceo_approval': 'set default',
        },
    )

    prepared_by_id = fields.Many2one('res.users', string='Prepared By', copy=False, readonly=True, tracking=True)
    prepared_date = fields.Datetime(string='Prepared On', copy=False, readonly=True)
    finance_approver_id = fields.Many2one('res.users', string='Finance Approver', copy=False, readonly=True, tracking=True)
    finance_approval_date = fields.Datetime(string='Finance Approved On', copy=False, readonly=True)
    ceo_approver_id = fields.Many2one('res.users', string='CEO Approver', copy=False, readonly=True, tracking=True)
    ceo_approval_date = fields.Datetime(string='CEO Approved On', copy=False, readonly=True)
    
    # Field mpya ya sababu ya kukataa
    reject_reason = fields.Text(string='Rejection Reason', copy=False, readonly=True, tracking=True)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _bic_notify_group(self, group_xmlid, summary):
        group = self.env.ref(group_xmlid)
        users = self.env['res.users'].sudo().search([('groups_id', 'in', group.id), ('share', '=', False)])
        for order in self:
            for user in users:
                order.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=user.id,
                    summary=summary,
                )

    def _bic_clear_activities(self):
        self.sudo().activity_unlink(['mail.mail_activity_data_todo'])

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------
    def button_confirm(self):
        if self.env.context.get('bic_skip_approval'):
            return super().button_confirm()

        for order in self.filtered(lambda o: o.state in ('draft', 'sent')):
            if not order.order_line:
                raise UserError(_("You cannot send an order without lines for approval."))
            order.write({
                'state': 'finance_approval',
                'prepared_by_id': self.env.user.id,
                'prepared_date': fields.Datetime.now(),
                'finance_approver_id': False,
                'finance_approval_date': False,
                'ceo_approver_id': False,
                'ceo_approval_date': False,
                'reject_reason': False,
            })
            order.message_post(body=_("Purchase Order submitted for Finance approval by %s.", self.env.user.name))
            order._bic_notify_group(FINANCE_GROUP, _("Finance approval required"))
        return True

    def action_finance_approve(self):
        if not self.env.user.has_group(FINANCE_GROUP):
            raise UserError(_("Only a Finance Approver can perform this action."))
        for order in self:
            if order.state != 'finance_approval':
                raise UserError(_("Order %s is not waiting for Finance approval.", order.name))
            order.write({
                'state': 'ceo_approval',
                'finance_approver_id': self.env.user.id,
                'finance_approval_date': fields.Datetime.now(),
            })
            order._bic_clear_activities()
            order.message_post(body=_("Approved by Finance: %s. Waiting for CEO approval.", self.env.user.name))
            order._bic_notify_group(CEO_GROUP, _("CEO approval required"))
        return True

    def action_ceo_approve(self):
        if not self.env.user.has_group(CEO_GROUP):
            raise UserError(_("Only the CEO Approver can perform this action."))
        for order in self:
            if order.state != 'ceo_approval':
                raise UserError(_("Order %s is not waiting for CEO approval.", order.name))
            order.write({
                'ceo_approver_id': self.env.user.id,
                'ceo_approval_date': fields.Datetime.now(),
            })
            order._bic_clear_activities()
            order.message_post(body=_("Approved by CEO: %s. Order confirmed.", self.env.user.name))
            
            order.write({'state': 'draft'})
            order.with_context(bic_skip_approval=True).button_confirm()
        return True

    def action_bic_reject_wizard(self):
        """Inafungua pop-up wizard ya kuandika sababu ya reject"""
        if not (self.env.user.has_group(FINANCE_GROUP) or self.env.user.has_group(CEO_GROUP)):
            raise UserError(_("Only approvers can reject an order."))
        return {
            'name': _('Reason for Rejection'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_order_id': self.id},
        }

    def button_draft(self):
        res = super().button_draft()
        self.write({
            'prepared_by_id': False, 'prepared_date': False,
            'finance_approver_id': False, 'finance_approval_date': False,
            'ceo_approver_id': False, 'ceo_approval_date': False,
            'reject_reason': False,
        })
        return res


class PurchaseOrderRejectWizard(models.TransientModel):
    _name = 'purchase.order.reject.wizard'
    _description = 'Purchase Order Reject Wizard'

    order_id = fields.Many2one('purchase.order', string='Purchase Order', required=True)
    reject_reason = fields.Text(string='Reason for Rejection', required=True)

    def action_confirm_rejection(self):
        self.ensure_one()
        order = self.order_id
        order.write({
            'state': 'draft',
            'reject_reason': self.reject_reason,
        })
        order._bic_clear_activities()
        order.message_post(body=_(
            "Approval rejected by <b>%s</b>.<br/><b>Reason:</b> %s", 
            self.env.user.name, 
            self.reject_reason
        ))
        return True