# -*- coding: utf-8 -*-

import logging

from markupsafe import Markup

from odoo import _, models

_logger = logging.getLogger(__name__)

INTERCOMPANY_TYPES = ('out_invoice', 'out_refund', 'in_invoice', 'in_refund')


class AccountMoveIntercompany(models.Model):
    _inherit = 'account.move'

    def _post(self, soft=True):
        posted = super()._post(soft=soft)
        for move in posted.filtered(lambda m: m.move_type in INTERCOMPANY_TYPES):
            try:
                with self.env.cr.savepoint():
                    move._notify_intercompany_company()
            except Exception:  # a notification problem must never block posting
                _logger.exception("Intercompany notification failed for %s", move.display_name)
        return posted

    def _notify_intercompany_company(self):
        """ If the partner is another company of this database, tell that company's accountants. """
        self.ensure_one()
        partner = self.partner_id.commercial_partner_id
        other_company = self.env['res.company'].sudo().search(
            [('partner_id', '=', partner.id), ('id', '!=', self.company_id.id)], limit=1)
        if not other_company:
            return
        group = self.env.ref('account.group_account_manager')
        users = self.env['res.users'].sudo().search([
            ('company_ids', 'in', other_company.id),
            ('groups_id', 'in', group.id),
            ('share', '=', False),
        ])
        if not users:
            return
        kinds = {
            'out_invoice': _("a customer invoice"),
            'out_refund': _("a credit note"),
            'in_invoice': _("a vendor bill"),
            'in_refund': _("a vendor credit note"),
        }
        text = _(
            "%(company)s has recorded %(kind)s %(name)s of %(amount)s %(currency)s with your company "
            "(%(other)s). Please check it and record the matching entry.",
            company=self.company_id.name, kind=kinds[self.move_type], name=self.name or '',
            amount=self.amount_total, currency=self.currency_id.name, other=other_company.name,
        )
        self.sudo().message_notify(
            partner_ids=users.partner_id.ids,
            subject=_("Intercompany transaction from %s", self.company_id.name),
            body=Markup("<p>%s</p>") % text,
            email_layout_xmlid='mail.mail_notification_light',
        )
