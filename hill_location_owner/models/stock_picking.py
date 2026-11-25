from odoo import api, fields, models, _
from odoo.exceptions import UserError

from .view_utils import inject_picking_form


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
    is_dest_owner = fields.Boolean(compute='_compute_owner_flags')
    hide_validation_buttons = fields.Boolean(compute='_compute_owner_flags')
    hide_dest_buttons = fields.Boolean(compute='_compute_owner_flags')

    # ------------------------------------------------------------------
    # Views
    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == 'form':
            inject_picking_form(arch)
        return arch, view

    # ------------------------------------------------------------------
    # Rules
    def _requires_owner_validation(self):
        self.ensure_one()
        return (self.picking_type_code == 'internal'
                and bool(self.location_dest_owner_ids)
                and self.state not in ('done', 'cancel'))

    def _owner_validation_blocked(self, user):
        """True when `user` may NOT use Validate / Mark as Todo at the current step."""
        self.ensure_one()
        if not self._requires_owner_validation():
            return False
        src, dest = self.location_owner_ids, self.location_dest_owner_ids
        if self.pending_validation:
            return user not in dest      # step 2: any destination owner
        if src:
            return user not in src       # step 1: any source owner
        return user in dest              # no source owner: anyone except destination owners

    @api.depends('location_owner_ids', 'location_dest_owner_ids', 'pending_validation',
                 'state', 'picking_type_code')
    @api.depends_context('uid')
    def _compute_owner_flags(self):
        user = self.env.user
        for picking in self:
            src, dest = picking.location_owner_ids, picking.location_dest_owner_ids
            requires = picking._requires_owner_validation()
            picking.is_dest_owner = user in dest
            picking.hide_validation_buttons = picking._owner_validation_blocked(user)
            # destination owners see NO button until a source owner made it pending
            picking.hide_dest_buttons = bool(
                requires and user in dest and user not in src and not picking.pending_validation)

    # ------------------------------------------------------------------
    # Workflow
    def _set_pending_validation(self):
        now = fields.Datetime.now()
        for picking in self:
            owners = picking.location_dest_owner_ids
            picking.write({
                'pending_validation': True,
                'pending_validation_user_id': self.env.user.id,
                'pending_validation_date': now,
            })
            picking.message_post(
                body=_('%(user)s requested validation of this transfer. Waiting for one of: '
                       '%(owners)s (owners of %(location)s).',
                       user=self.env.user.name, owners=_names(owners),
                       location=picking.location_dest_id.display_name),
                partner_ids=owners.partner_id.ids,
                message_type='comment', subtype_xmlid='mail.mt_comment')
            for owner in owners:
                picking.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=owner.id,
                    summary=_('Validate internal transfer %s', picking.name),
                    note=_('Requested by %s.', self.env.user.name))

    def action_confirm(self):
        # server-side twin of the hidden "Mark as Todo" button (sudo/cron are not restricted)
        if not self.env.su:
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
            src, dest = picking.location_owner_ids, picking.location_dest_owner_ids
            if user in src and user in dest:
                continue  # owns both sides: validate directly
            if picking.pending_validation:
                if user not in dest:
                    raise UserError(_(
                        '%(name)s is waiting for validation by one of: %(owners)s. '
                        'Only a destination location owner can validate it.',
                        name=picking.name, owners=_names(dest)))
                continue
            # step 1: not pending yet
            if user in dest:
                raise UserError(_(
                    '%(name)s must first be validated by a source location owner (%(owners)s).',
                    name=picking.name, owners=_names(src)))
            if src and user not in src:
                raise UserError(_(
                    'Only a source location owner (%(owners)s) can validate %(name)s first.',
                    owners=_names(src), name=picking.name))
            to_pending |= picking

        if to_pending:
            to_pending._set_pending_validation()
            remaining = self - to_pending
            if remaining:
                return super(StockPicking, remaining).button_validate()
            owners = _names(to_pending.location_dest_owner_ids)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Pending Validation'),
                    'message': _('Waiting for one of: %s to validate this transfer.', owners),
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
            # closes the todo of every destination owner, not only the one who validated
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
                             owners=_names(self.location_dest_owner_ids),
                             user=self.pending_validation_user_id.name or '-'),
                'type': 'info',
                'sticky': False,
            },
        }

    def action_reject_pending_validation(self):
        for picking in self:
            if self.env.user not in picking.location_dest_owner_ids:
                raise UserError(_('Only a destination location owner can reject this validation.'))
            requester = picking.pending_validation_user_id
            picking.activity_unlink(['mail.mail_activity_data_todo'])
            picking.write({'pending_validation': False})
            picking.message_post(
                body=_('%s rejected the validation request.', self.env.user.name),
                partner_ids=requester.partner_id.ids,
                message_type='comment', subtype_xmlid='mail.mt_comment')
        return True
