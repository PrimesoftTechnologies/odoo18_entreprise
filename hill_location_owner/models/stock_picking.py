from odoo import api, fields, models, _
from odoo.exceptions import UserError

from .view_utils import CONFIRM_CONTEXT_KEY, inject_picking_form

# Picking types that go through the owner validation flow
OWNER_VALIDATION_TYPES = ('internal', 'incoming', 'outgoing')


def _names(users):
    return ', '.join(users.mapped('name')) or '-'


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # Owners come from the chosen locations (Inventory > Configuration > Locations)
    location_owner_ids = fields.Many2many(
        'res.users', string='Source Location Owners',
        related='location_id.location_owner_ids', readonly=True)
    location_dest_owner_ids = fields.Many2many(
        'res.users', string='Destination Location Owners',
        related='location_dest_id.location_owner_ids', readonly=True)

    pending_validation = fields.Boolean(
        string='Pending Validation', copy=False, tracking=True)
    pending_validation_user_id = fields.Many2one(
        'res.users', string='Validation Requested By', copy=False, readonly=True)
    pending_validation_date = fields.Datetime(
        string='Validation Requested On', copy=False, readonly=True)

    # UI helpers (depend on the current user)
    is_approver = fields.Boolean(compute='_compute_owner_flags')
    hide_validation_buttons = fields.Boolean(compute='_compute_owner_flags')
    hide_approver_buttons = fields.Boolean(compute='_compute_owner_flags')

    # ------------------------------------------------------------------
    # Views
    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == 'form':
            inject_picking_form(arch)
        return arch, view

    # ------------------------------------------------------------------
    # Roles
    #   approvers: owners who give the FINAL validation (they receive or hand over the goods)
    #   starters : owners of the other side who make the transfer "pending" (may be empty;
    #              then any user who is not an approver can start it)
    #
    #   Internal / Receipt / Pick components -> approvers = destination owners
    #   Delivery                             -> approvers = source owners
    #   (Pick components are ordinary internal transfers: stock -> production location)
    def _approver_is_source(self):
        self.ensure_one()
        return self.picking_type_code == 'outgoing'

    def _get_owner_roles(self):
        """Return (starters, approvers) as res.users recordsets."""
        self.ensure_one()
        src, dest = self.location_owner_ids, self.location_dest_owner_ids
        return (dest, src) if self._approver_is_source() else (src, dest)

    def _get_approver_location(self):
        self.ensure_one()
        return self.location_id if self._approver_is_source() else self.location_dest_id

    # ------------------------------------------------------------------
    # Rules
    def _requires_owner_validation(self):
        self.ensure_one()
        return (self.picking_type_code in OWNER_VALIDATION_TYPES
                and bool(self._get_owner_roles()[1])
                and self.state not in ('done', 'cancel'))

    def _owner_validation_blocked(self, user):
        """True when `user` may NOT use Validate / Mark as Todo at the current step."""
        self.ensure_one()
        if not self._requires_owner_validation():
            return False
        starters, approvers = self._get_owner_roles()
        if self.pending_validation:
            return user not in approvers     # step 2: any approver
        if starters:
            return user not in starters      # step 1: any starter
        return user in approvers             # no starters: anyone except the approvers

    @api.depends('location_owner_ids', 'location_dest_owner_ids', 'pending_validation',
                 'state', 'picking_type_code')
    @api.depends_context('uid')
    def _compute_owner_flags(self):
        user = self.env.user
        for picking in self:
            starters, approvers = picking._get_owner_roles()
            requires = picking._requires_owner_validation()
            picking.is_approver = user in approvers
            picking.hide_validation_buttons = picking._owner_validation_blocked(user)
            # approvers see NO button until a starter made the transfer pending
            picking.hide_approver_buttons = bool(
                requires and user in approvers and user not in starters
                and not picking.pending_validation)

    # ------------------------------------------------------------------
    # Workflow
    def _set_pending_validation(self):
        now = fields.Datetime.now()
        for picking in self:
            approvers = picking._get_owner_roles()[1]
            picking.write({
                'pending_validation': True,
                'pending_validation_user_id': self.env.user.id,
                'pending_validation_date': now,
            })
            picking.message_post(
                body=_('%(user)s requested validation of this transfer. Waiting for one of: '
                       '%(owners)s (owners of %(location)s).',
                       user=self.env.user.name, owners=_names(approvers),
                       location=picking._get_approver_location().display_name),
                partner_ids=approvers.partner_id.ids,
                message_type='comment', subtype_xmlid='mail.mt_comment')
            for owner in approvers:
                picking.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=owner.id,
                    summary=_('Validate transfer %s', picking.name),
                    note=_('Requested by %s.', self.env.user.name))
                # live bell for approvers who are already logged in (see static/src/js)
                self.env['bus.bus']._sendone(
                    owner.partner_id, 'hill_location_owner/pending_approval', {
                        'picking_id': picking.id,
                        'name': picking.name,
                        'requested_by': self.env.user.name,
                    })

    @api.model
    def get_my_pending_approvals(self):
        """Transfers waiting for the current user's approval (used by the login bell)."""
        activities = self.env['mail.activity'].search([
            ('res_model', '=', 'stock.picking'),
            ('user_id', '=', self.env.uid),
            ('activity_type_id', '=', self.env.ref('mail.mail_activity_data_todo').id),
        ])
        pickings = self.browse(activities.mapped('res_id')).exists().filtered(
            lambda p: p.pending_validation and p.state not in ('done', 'cancel'))
        return [{'id': p.id, 'name': p.name} for p in pickings]

    @api.model
    def acknowledge_pending_approvals(self, picking_ids):
        """The approver opened the transfer from the bell: remove HIS to-do activity only.

        The transfer stays pending and the other approvers keep their activity.
        """
        pickings = self.browse(picking_ids).exists().filtered('pending_validation')
        self.env['mail.activity'].sudo().search([
            ('res_model', '=', 'stock.picking'),
            ('res_id', 'in', pickings.ids),
            ('user_id', '=', self.env.uid),
            ('activity_type_id', '=', self.env.ref('mail.mail_activity_data_todo').id),
        ]).unlink()
        return True

    def action_confirm(self):
        # Server-side twin of the hidden "Mark as Todo" button. Only the button sends the
        # context flag, so automatic flows (sale, purchase, POS, MRP, returns) are never blocked.
        if not self.env.su and self.env.context.get(CONFIRM_CONTEXT_KEY):
            for picking in self:
                if picking._owner_validation_blocked(self.env.user):
                    raise UserError(_(
                        'You are not allowed to confirm %s at this step of the owner validation.',
                        picking.name))
        return super().action_confirm()

    def button_validate(self):
        user = self.env.user
        to_pending = self.browse()
        for picking in self:
            if not picking._requires_owner_validation():
                continue
            starters, approvers = picking._get_owner_roles()
            if user in starters and user in approvers:
                continue  # owns both sides: validate directly
            if picking.pending_validation:
                if user not in approvers:
                    raise UserError(_(
                        '%(name)s is waiting for validation by one of: %(owners)s. '
                        'Only these location owners can validate it.',
                        name=picking.name, owners=_names(approvers)))
                continue
            # step 1: not pending yet
            if user in approvers:
                if starters:
                    raise UserError(_(
                        '%(name)s must first be validated by one of: %(owners)s.',
                        name=picking.name, owners=_names(starters)))
                raise UserError(_(
                    '%(name)s must first be validated by another user who is not an owner of %(location)s.',
                    name=picking.name, location=picking._get_approver_location().display_name))
            if starters and user not in starters:
                raise UserError(_(
                    'Only one of: %(owners)s can validate %(name)s first.',
                    owners=_names(starters), name=picking.name))
            to_pending |= picking

        if to_pending:
            to_pending._set_pending_validation()
            remaining = self - to_pending
            if remaining:
                return super(StockPicking, remaining).button_validate()
            approvers = self.env['res.users']
            for picking in to_pending:
                approvers |= picking._get_owner_roles()[1]
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Pending Validation'),
                    'message': _('Waiting for one of: %s to validate this transfer.',
                                 _names(approvers)),
                    'type': 'warning',
                    'sticky': False,
                    'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'},
                },
            }
        return super().button_validate()

    def _action_done(self):
        pendings = self.filtered('pending_validation')
        res = super()._action_done()
        if pendings:
            # closes the todo of every approver, not only the one who validated
            pendings.activity_feedback(['mail.mail_activity_data_todo'])
            pendings.write({'pending_validation': False})
        return res

    # ------------------------------------------------------------------
    def action_pending_validation_info(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Pending Validation'),
                'message': _('Waiting for one of: %(owners)s to validate this transfer '
                             '(requested by %(user)s).',
                             owners=_names(self._get_owner_roles()[1]),
                             user=self.pending_validation_user_id.name or '-'),
                'type': 'info',
                'sticky': False,
            },
        }

    def action_reject_pending_validation(self):
        for picking in self:
            if self.env.user not in picking._get_owner_roles()[1]:
                raise UserError(_('Only a location owner who must validate this transfer can reject it.'))
            requester = picking.pending_validation_user_id
            picking.activity_unlink(['mail.mail_activity_data_todo'])
            picking.write({'pending_validation': False})
            picking.message_post(
                body=_('%s rejected the validation request.', self.env.user.name),
                partner_ids=requester.partner_id.ids,
                message_type='comment', subtype_xmlid='mail.mt_comment')
        return True
