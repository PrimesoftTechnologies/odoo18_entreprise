# -*- coding: utf-8 -*-

from markupsafe import Markup

from odoo import _, fields, models
from odoo.tools import float_is_zero

from .mrp_production import PROD_GROUP


class MrpProductionVariance(models.Model):
    _inherit = 'mrp.production'

    planned_qty = fields.Float(
        string='Planned Quantity', copy=False, readonly=True, digits='Product Unit of Measure',
        help="Quantity planned when the Manufacturing Order was confirmed.",
    )

    def action_confirm(self):
        res = super().action_confirm()
        for production in self.filtered(lambda p: not p.planned_qty):
            production.planned_qty = production.product_qty
        return res

    def write(self, vals):
        newly_done = self.env['mrp.production']
        if vals.get('state') == 'done':
            newly_done = self.filtered(lambda p: p.state != 'done')
        res = super().write(vals)
        for production in newly_done:
            production._notify_quantity_variance()
        return res

    def _notify_quantity_variance(self):
        self.ensure_one()
        planned = self.planned_qty
        if not planned:
            return
        produced = self.qty_produced
        difference = produced - planned
        if float_is_zero(difference, precision_rounding=self.product_uom_id.rounding):
            return
        percent = difference / planned * 100
        partners = (self._users_in_group(PROD_GROUP).partner_id
                    | self.create_uid.partner_id | self.user_id.partner_id)
        text = _(
            "Quantity variance on %(name)s: planned %(planned)s, produced %(produced)s %(uom)s "
            "(difference %(diff)s, %(pct).1f%%).",
            name=self.name, planned=planned, produced=produced, uom=self.product_uom_id.name,
            diff=difference, pct=percent,
        )
        self.message_post(
            body=Markup("<p>%s</p>") % text,
            partner_ids=partners.ids,
            subtype_xmlid='mail.mt_comment',
        )
