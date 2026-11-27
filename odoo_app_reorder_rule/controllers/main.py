import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

# JavaScript appended to Odoo's service worker. When ANY push arrives (even
# when the app is closed) it asks the server for the number of open reorder
# alerts and sets it as the app icon badge (Android / iOS PWA / desktop PWA).
REORDER_BADGE_SW = r"""
/* ---- odoo_app_reorder_rule: app icon badge on push ---- */
(function () {
    const COUNT_URL = "/reorder_alert/badge_count";
    async function updateReorderBadge() {
        const nav = self.navigator;
        if (!nav || !nav.setAppBadge) {
            return;
        }
        let count = null;
        try {
            const resp = await fetch(COUNT_URL, {
                credentials: "same-origin",
                headers: { Accept: "application/json" },
            });
            if (resp.ok) {
                const data = await resp.json();
                if (typeof data.count === "number") {
                    count = data.count;
                }
            }
        } catch (e) {
            // offline or session expired: fall back to a generic badge
        }
        try {
            if (count === null) {
                await nav.setAppBadge();
            } else if (count > 0) {
                await nav.setAppBadge(count);
            } else {
                await nav.clearAppBadge();
            }
        } catch (e) {
            // badge not supported on this device
        }
    }
    self.addEventListener("push", function (event) {
        event.waitUntil(updateReorderBadge());
    });
})();
"""


class ReorderAlertBadge(http.Controller):

    @http.route("/reorder_alert/badge_count", type="http", auth="user", methods=["GET"])
    def badge_count(self, **kwargs):
        state = request.env["reorder.alert"].get_alert_state()
        return request.make_json_response({"count": state["count"]})


try:
    from odoo.addons.web.controllers.webmanifest import WebManifest
except ImportError:  # pragma: no cover
    WebManifest = None
    _logger.warning("WebManifest controller not found: service worker badge disabled")

if WebManifest is not None:

    class ReorderAlertWebManifest(WebManifest):

        def _get_service_worker_content(self):
            content = super()._get_service_worker_content()
            if isinstance(content, bytes):
                return content + b"\n" + REORDER_BADGE_SW.encode()
            return content + "\n" + REORDER_BADGE_SW
