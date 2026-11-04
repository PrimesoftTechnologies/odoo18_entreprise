from odoo import api, fields, models, _
from odoo.exceptions import UserError

from .view_utils import inject_picking_form


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    location_owner_id = fields.Many2one(
        'res.users', string='Source Location Owner',
        related='location_id.location_owner_id', readonly=True)
    location_dest_owner_id = fields.Many2one(
        'res.users', string='Destination Location Owner',
        related='location_dest_id.location_owner_id', readonly=True)
    pending_validation = fields.Boolean(
        string='Pending Validation', copy=False, tracking=True)
    pending_validation_user_id = fields.Many2one(
        'res.users', string='Validation Requested By', copy=False, readonly=True)
    pending_validation_date = fields.Datetime(
        string='Validation Requested On', copy=False, readonly=True)
    obama_request_id = fields.Many2one(
        'purchase.request', string='Purchase Request', copy=False, ondelete='set null')
    is_dest_owner = fields.Boolean(compute='_compute_is_dest_owner')
    hide_validation_buttons = fields.Boolean(compute='_compute_is_dest_owner')
    hide_dest_buttons = fields.Boolean(compute='_compute_is_dest_owner')

    # ------------------------------------------------------------------
    # Transfers opened from a Purchase Request start with EMPTY locations
    def _compute_location_id(self):
        super()._compute_location_id()
        if self.env.context.get('clear_picking_locations'):
            for picking in self.filtered(lambda p: not p._origin):
                picking.location_id = False

    def _compute_location_dest_id(self):
        super()._compute_location_dest_id()
        if self.env.context.get('clear_picking_locations'):
            for picking in self.filtered(lambda p: not p._origin):
                picking.location_dest_id = False

    # ------------------------------------------------------------------
    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == 'form':
            inject_picking_form(arch)
        return arch, view

    @api.depends('location_owner_id', 'location_dest_owner_id', 'pending_validation',
                 'state', 'picking_type_code')
    @api.depends_context('uid')
    def _compute_is_dest_owner(self):
        user = self.env.user
        for picking in self:
            src, dest = picking.location_owner_id, picking.location_dest_owner_id
            picking.is_dest_owner = bool(dest and dest == user)
            hide = False
            if picking._requires_owner_validation():
                if picking.pending_validation:
                    # step 2: only the destination owner validates
                    hide = dest != user
                elif src:
                    # step 1: only the source owner starts the validation
                    hide = src != user
                else:
                    # no source owner: anyone except the destination owner
                    hide = dest == user
            picking.hide_validation_buttons = hide
            # destination owner sees NO button until the source owner made it pending
            picking.hide_dest_buttons = bool(
                picking._requires_owner_validation()
                and dest == user and src != user
                and not picking.pending_validation)

    def _requires_owner_validation(self):
        self.ensure_one()
        return (self.picking_type_code == 'internal'
                and bool(self.location_dest_owner_id)
                and self.state not in ('done', 'cancel'))

    # ------------------------------------------------------------------
    def _set_pending_validation(self):
        now = fields.Datetime.now()
        for picking in self:
            owner = picking.location_dest_owner_id
            picking.write({
                'pending_validation': True,
                'pending_validation_user_id': self.env.user.id,
                'pending_validation_date': now,
            })
            picking.message_post(
                body=_('%(user)s requested validation of this transfer. Waiting for %(owner)s, '
                       'owner of %(location)s, to validate.',
                       user=self.env.user.name, owner=owner.name,
                       location=picking.location_dest_id.display_name),
                partner_ids=owner.partner_id.ids,
                message_type='comment', subtype_xmlid='mail.mt_comment')
            picking.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=owner.id,
                summary=_('Validate internal transfer %s', picking.name),
                note=_('Requested by %s.', self.env.user.name))

    def button_validate(self):
        user = self.env.user
        to_pending = self.browse()
        for picking in self:
            if not picking._requires_owner_validation():
                continue
            src, dest = picking.location_owner_id, picking.location_dest_owner_id
            if src == user and dest == user:
                continue  # same person owns both locations: validate directly
            if picking.pending_validation:
                if dest != user:
                    raise UserError(_(
                        '%(name)s is waiting for validation by %(owner)s. '
                        'Only the destination location owner can validate it.',
                        name=picking.name, owner=dest.name))
                continue
            # step 1: not pending yet
            if dest == user:
                raise UserError(_(
                    '%(name)s must first be validated by the source location owner%(who)s.',
                    name=picking.name, who=' (%s)' % src.name if src else ''))
            if src and src != user:
                raise UserError(_(
                    'Only the source location owner (%(owner)s) can validate %(name)s first.',
                    owner=src.name, name=picking.name))
            to_pending |= picking

        if to_pending:
            to_pending._set_pending_validation()
            remaining = self - to_pending
            if remaining:
                return super(StockPicking, remaining).button_validate()
            owners = ', '.join(to_pending.mapped('location_dest_owner_id.name'))
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Pending Validation'),
                    'message': _('Waiting for %s to validate this transfer.', owners),
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
                'message': _('Waiting for %(owner)s to validate this transfer (requested by %(user)s).',
                             owner=self.location_dest_owner_id.name or '-',
                             user=self.pending_validation_user_id.name or '-'),
                'type': 'info',
                'sticky': False,
            },
        }

    def action_reject_pending_validation(self):
        for picking in self:
            if picking.location_dest_owner_id != self.env.user:
                raise UserError(_('Only the destination location owner can reject this validation.'))
            requester = picking.pending_validation_user_id
            picking.activity_unlink(['mail.mail_activity_data_todo'])
            picking.write({'pending_validation': False})
            picking.message_post(
                body=_('%s rejected the validation request.', self.env.user.name),
                partner_ids=requester.partner_id.ids,
                message_type='comment', subtype_xmlid='mail.mt_comment')
        return True
