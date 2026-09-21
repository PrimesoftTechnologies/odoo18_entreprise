from odoo import models, fields, api, exceptions, _

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('wait_approval', 'Wait for Approval'),
            ('approved', 'Approved'),
            ('confirmed', 'Confirmed'),
            ('wait_transfer', 'Wait for Transfer'),
            ('ready_to_produce', 'Ready to Produce'),
            ('close_production', 'Close for Production'),
            ('done', 'Done'),
            ('cancel', 'Cancelled'),
            ('reject', 'Rejected'),
        ],
        string='Status', readonly=True, copy=False, index=True, tracking=True, default='draft',
        ondelete={
            'draft': 'cascade',
            'wait_approval': 'cascade',
            'approved': 'cascade',
            'confirmed': 'cascade',
            'wait_transfer': 'cascade',
            'ready_to_produce': 'cascade',
            'close_production': 'cascade',
            'done': 'cascade',
            'cancel': 'cascade',
            'reject': 'cascade',
        },
    )

    is_approval_flow_enabled = fields.Boolean(string="Approval Flow Enabled", compute='_compute_workflow_enabled')
    is_inspection_flow_enabled = fields.Boolean(string="Inspection Flow Enabled", compute='_compute_workflow_enabled')
    can_approve = fields.Boolean(string="Can Approve", compute='_compute_workflow_permissions')
    can_request_approval = fields.Boolean(string="Can Request Approval", compute='_compute_workflow_permissions')
    requested_by = fields.Many2one('res.users', string="Requested By", readonly=True, copy=False, tracking=True)

    def _refresh_activity(self, user_ids, message):
        for order in self:
            order.activity_ids.filtered(lambda a: a.res_id == order.id and a.state != 'done').action_done()
            for user in user_ids:
                order.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=user.id,
                    summary=_('Manufacturing Action Required'),
                    note=_(message),
                )

    @api.depends('company_id')
    def _compute_workflow_enabled(self):
        Param = self.env['ir.config_parameter'].sudo()
        for order in self:
            company_id = order.company_id.id if order.company_id else False
            approval_value = Param.get_param(f'approval_manufacturing_custom.use_approval_flow_{company_id}', default='False')
            inspection_value = Param.get_param(f'approval_manufacturing_custom.use_inspection_flow_{company_id}', default='False')
            order.is_approval_flow_enabled = str(approval_value).lower() in ('true', '1')
            order.is_inspection_flow_enabled = str(inspection_value).lower() in ('true', '1')

    @api.depends('company_id', 'company_id.manufacturing_approver_ids', 'requested_by')
    def _compute_workflow_permissions(self):
        current_user = self.env.user
        for order in self:
            approvers = order.company_id.manufacturing_approver_ids if order.company_id else self.env['res.users']
            order.can_approve = (current_user in approvers)
            order.can_request_approval = (current_user not in approvers)

    def button_mark_done(self):
        for order in self:
            if order.is_approval_flow_enabled and order.is_inspection_flow_enabled:
                if order.state == 'ready_to_produce':
                    res = super(MrpProduction, order).button_mark_done()
                    order.state = 'close_production'
                    order._refresh_activity(
                        order.company_id.manufacturing_approver_ids,
                        f"Manufacturing Order {order.name} production is done and waiting for final closing."
                    )
                    return res
                elif order.state == 'close_production':
                    return super(MrpProduction, order).button_mark_done()
                else:
                    raise exceptions.UserError(_("You are not allowed to produce at this stage."))
            return super(MrpProduction, order).button_mark_done()
        return True

    def action_request_approval(self):
        for order in self:
            if self.env.user in order.company_id.manufacturing_approver_ids:
                raise exceptions.AccessError(_("Approvers are not allowed to submit manufacturing orders for approval."))
            if not order.requested_by:
                order.requested_by = self.env.user
            order.state = 'wait_approval'
            order._refresh_activity(
                order.company_id.manufacturing_approver_ids,
                f"Manufacturing Order {order.name} is waiting for your approval."
            )
        return True

    def action_approve(self):
        for order in self:
            if order.state != 'wait_approval':
                raise exceptions.UserError(_("This Manufacturing Order is not waiting for approval."))
            if self.env.user not in order.company_id.manufacturing_approver_ids:
                raise exceptions.AccessError(_("You are not authorized to approve this order."))
            order.state = 'approved'
            target_users = order.requested_by if order.requested_by else order.company_id.manufacturing_inspector_ids
            order._refresh_activity(
                target_users,
                f"Manufacturing Order {order.name} has been approved and requires your confirmation."
            )
        return True

    def action_custom_confirm(self):
        for order in self:
            if order.state != 'approved':
                raise exceptions.UserError(_("Order must be approved before confirmation."))
            if order.requested_by and self.env.user != order.requested_by:
                raise exceptions.AccessError(_("Only the user who originally requested this Manufacturing Order can confirm it."))

            order.activity_ids.filtered(lambda a: a.res_id == order.id and a.state != 'done').action_done()
            order.with_context(skip_activity=True).write({'state': 'draft'})
            
            res = super(MrpProduction, order).action_confirm()
            order.state = 'wait_transfer'
            return res
        return True

    def _check_order(self):
        """Hapa Odoo inaangalia kama transfer imeshavalidishwa, ikiwa done, inabadilisha state kuwa ready_to_produce ili Produce All ije"""
        res = super(MrpProduction, self)._check_order()
        for order in self:
            if order.is_approval_flow_enabled and order.is_inspection_flow_enabled:
                if order.state == 'wait_transfer':
                    if order.picking_ids and all(p.state == 'done' for p in order.picking_ids):
                        order.state = 'ready_to_produce'
        return res

    def action_final_close_production(self):
        for order in self:
            if order.state != 'close_production':
                raise exceptions.UserError(_("Order is not ready for final closing."))
            if self.env.user not in order.company_id.manufacturing_approver_ids:
                raise exceptions.AccessError(_("Only Approvers can close the production."))
            return super(MrpProduction, order).button_mark_done()
        return True

    def action_open_reject_wizard(self):
        self.ensure_one()
        return {
            'name': _('Reject Manufacturing Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.production.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_production_id': self.id},
        }

class MrpProductionRejectWizard(models.TransientModel):
    _name = 'mrp.production.reject.wizard'
    _description = 'Manufacturing Order Reject Reason Wizard'

    production_id = fields.Many2one('mrp.production', string="Manufacturing Order", required=True)
    reason = fields.Text(string="Reason for Rejection", required=True)

    def action_confirm_reject(self):
        self.ensure_one()
        order = self.production_id
        order.state = 'draft'
        order.message_post(body=_(f"<b>Rejected & Reset to Draft by:</b> {self.env.user.name}<br/><b>Reason:</b> {self.reason}"))
        return {'type': 'ir.actions.act_window_close'}