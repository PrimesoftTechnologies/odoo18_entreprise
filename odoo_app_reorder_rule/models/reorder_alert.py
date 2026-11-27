import logging

from markupsafe import Markup

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


def _fmt(value):
    return "%g" % value


class ReorderAlert(models.Model):
    _name = "reorder.alert"
    _description = "Reorder Rule Alert"
    _order = "state, date_triggered desc, id desc"

    name = fields.Char(compute="_compute_name", store=True)
    orderpoint_id = fields.Many2one(
        "stock.warehouse.orderpoint", string="Reorder Rule",
        ondelete="cascade", index=True, required=True)
    product_id = fields.Many2one("product.product", string="Product", required=True, index=True)
    location_id = fields.Many2one("stock.location", string="Location")
    warehouse_id = fields.Many2one("stock.warehouse", string="Warehouse")
    company_id = fields.Many2one(
        "res.company", string="Company", required=True,
        default=lambda self: self.env.company)
    qty_on_hand = fields.Float(string="On Hand", digits="Product Unit of Measure")
    min_qty = fields.Float(string="Minimum", digits="Product Unit of Measure")
    shortage = fields.Float(
        string="Shortage", compute="_compute_shortage", store=True,
        digits="Product Unit of Measure")
    state = fields.Selection(
        [("open", "Open"), ("resolved", "Resolved")],
        default="open", required=True, index=True)
    date_triggered = fields.Datetime(default=fields.Datetime.now, readonly=True)
    date_resolved = fields.Datetime(readonly=True)

    @api.depends("product_id", "location_id")
    def _compute_name(self):
        for rec in self:
            rec.name = "%s @ %s" % (
                rec.product_id.display_name or "", rec.location_id.display_name or "")

    @api.depends("qty_on_hand", "min_qty")
    def _compute_shortage(self):
        for rec in self:
            rec.shortage = max(rec.min_qty - rec.qty_on_hand, 0.0)

    # ------------------------------------------------------------------
    # Core check
    # ------------------------------------------------------------------
    @api.model
    def _check_orderpoints(self, orderpoints):
        """Compare on-hand with minimum for each orderpoint.
        Creates an alert (and notifies) when below minimum, resolves it when back."""
        Alert = self.sudo()
        orderpoints = orderpoints.sudo()
        if not orderpoints:
            return Alert.browse()
        open_alerts = Alert.search([
            ("orderpoint_id", "in", orderpoints.ids), ("state", "=", "open")])
        open_map = {a.orderpoint_id.id: a for a in open_alerts}
        new_alerts = Alert.browse()
        for op in orderpoints:
            product = op.product_id
            below = False
            on_hand = 0.0
            if op.active and product and op.location_id:
                storable = product.is_storable if "is_storable" in product._fields else True
                if storable:
                    on_hand = product.with_company(op.company_id).with_context(
                        location=op.location_id.id).qty_available
                    below = on_hand < op.product_min_qty
            alert = open_map.get(op.id)
            if below:
                vals = {"qty_on_hand": on_hand, "min_qty": op.product_min_qty}
                if alert:
                    alert.write(vals)
                else:
                    vals.update({
                        "orderpoint_id": op.id,
                        "product_id": product.id,
                        "location_id": op.location_id.id,
                        "warehouse_id": op.warehouse_id.id,
                        "company_id": op.company_id.id,
                    })
                    new_alerts |= Alert.create(vals)
            elif alert:
                alert.write({
                    "state": "resolved",
                    "date_resolved": fields.Datetime.now(),
                    "qty_on_hand": on_hand,
                })
        if new_alerts:
            new_alerts._notify()
        return new_alerts

    @api.model
    def _check_products(self, products):
        orderpoints = self.env["stock.warehouse.orderpoint"].sudo().with_context(
            active_test=False).search([("product_id", "in", products.ids)])
        return self._check_orderpoints(orderpoints)

    @api.model
    def _cron_check_all(self):
        orderpoints = self.env["stock.warehouse.orderpoint"].sudo().with_context(
            active_test=False).search([])
        for i in range(0, len(orderpoints), 200):
            self._check_orderpoints(orderpoints[i:i + 200])
        return True

    # ------------------------------------------------------------------
    # Notifications
    # ------------------------------------------------------------------
    def _notify(self):
        group = self.env.ref(
            "odoo_app_reorder_rule.group_reorder_alert_receiver", raise_if_not_found=False)
        if not group:
            return
        for alert in self:
            users = self.env["res.users"].sudo().search([
                ("groups_id", "in", group.ids),
                ("share", "=", False),
                ("company_ids", "in", alert.company_id.id),
            ])
            partners = users.partner_id
            if not partners:
                continue
            title = _("Low stock: %s", alert.product_id.display_name)
            message = _(
                "On hand %(qty)s is below minimum %(min)s at %(loc)s",
                qty=_fmt(alert.qty_on_hand), min=_fmt(alert.min_qty),
                loc=alert.location_id.display_name or "")
            payload = {"id": alert.id, "title": title, "message": message}
            for partner in partners:
                self.env["bus.bus"]._sendone(partner, "reorder_alert", payload)
            body = Markup(
                "<p>%s</p><ul><li>%s: %s</li><li>%s: %s</li>"
                "<li>%s: %s</li><li>%s: %s</li></ul>") % (
                message,
                _("Product"), alert.product_id.display_name,
                _("Location"), alert.location_id.display_name or "",
                _("On hand"), _fmt(alert.qty_on_hand),
                _("Minimum"), _fmt(alert.min_qty),
            )
            try:
                with self.env.cr.savepoint():
                    self.env["mail.thread"].sudo().message_notify(
                        partner_ids=partners.ids,
                        subject=title,
                        body=body,
                        email_layout_xmlid="mail.mail_notification_light",
                    )
            except Exception:
                _logger.exception("Could not send reorder alert message")

    # ------------------------------------------------------------------
    # Used by the web client
    # ------------------------------------------------------------------
    @api.model
    def get_alert_state(self):
        user = self.env.user
        allowed = user.has_group("odoo_app_reorder_rule.group_reorder_alert_receiver") or \
            user.has_group("stock.group_stock_user")
        count = 0
        if allowed:
            count = self.search_count([("state", "=", "open")])
        return {"allowed": bool(allowed), "count": count}

    def action_open_orderpoint(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "stock.warehouse.orderpoint",
            "res_id": self.orderpoint_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_resolve(self):
        self.write({"state": "resolved", "date_resolved": fields.Datetime.now()})
