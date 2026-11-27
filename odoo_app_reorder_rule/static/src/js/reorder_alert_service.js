/** @odoo-module **/

import { registry } from "@web/core/registry";
import { reactive } from "@odoo/owl";

const ACTION = "odoo_app_reorder_rule.action_reorder_alert";

export const reorderAlertService = {
    dependencies: ["bus_service", "orm", "notification", "action"],

    start(env, { bus_service, orm, notification, action }) {
        const state = reactive({ count: 0, allowed: false });
        let originalIcon = null;

        // ---- Badge on the browser tab icon (favicon) -------------------
        function drawFaviconBadge(count) {
            const link = document.querySelector("link[rel~='icon']");
            if (!link) {
                return;
            }
            if (!originalIcon) {
                originalIcon = { href: link.href, type: link.type };
            }
            if (!count) {
                link.href = originalIcon.href;
                if (originalIcon.type) {
                    link.type = originalIcon.type;
                }
                return;
            }
            const img = new Image();
            img.onload = () => {
                const size = 64;
                const canvas = document.createElement("canvas");
                canvas.width = size;
                canvas.height = size;
                const ctx = canvas.getContext("2d");
                ctx.drawImage(img, 0, 0, size, size);
                ctx.beginPath();
                ctx.arc(44, 20, 20, 0, 2 * Math.PI);
                ctx.fillStyle = "#e11d48";
                ctx.fill();
                ctx.fillStyle = "#ffffff";
                ctx.font = "bold 26px sans-serif";
                ctx.textAlign = "center";
                ctx.textBaseline = "middle";
                ctx.fillText(count > 99 ? "99+" : String(count), 44, 21);
                link.type = "image/png";
                link.href = canvas.toDataURL("image/png");
            };
            img.src = originalIcon.href;
        }

        // ---- Badge on installed app icon (PWA) + tab icon ---------------
        function updateBadges() {
            try {
                if (navigator.setAppBadge) {
                    if (state.count > 0) {
                        navigator.setAppBadge(state.count);
                    } else {
                        navigator.clearAppBadge();
                    }
                }
            } catch (e) {
                // ignore
            }
            try {
                drawFaviconBadge(state.count);
            } catch (e) {
                // ignore
            }
        }

        async function refresh() {
            try {
                const res = await orm.call("reorder.alert", "get_alert_state", []);
                state.count = res.count;
                state.allowed = res.allowed;
            } catch (e) {
                state.count = 0;
                state.allowed = false;
            }
            updateBadges();
        }

        function openAlerts() {
            action.doAction(ACTION);
        }

        // ---- Desktop (browser) notification ----------------------------
        function browserNotify(payload) {
            if (!("Notification" in window) || Notification.permission !== "granted") {
                return;
            }
            try {
                const n = new Notification(payload.title, {
                    body: payload.message,
                    tag: "reorder-alert-" + payload.id,
                    requireInteraction: true,
                });
                n.onclick = () => {
                    window.focus();
                    openAlerts();
                    n.close();
                };
            } catch (e) {
                // ignore
            }
        }

        if ("Notification" in window && Notification.permission === "default") {
            // browsers require a user gesture to ask for permission
            document.addEventListener(
                "click",
                () => Notification.requestPermission(),
                { once: true }
            );
        }

        bus_service.subscribe("reorder_alert", async (payload) => {
            await refresh();
            notification.add(payload.message, {
                title: payload.title,
                type: "danger",
                sticky: true,
                buttons: [
                    {
                        name: "View alerts",
                        onClick: openAlerts,
                        primary: true,
                    },
                ],
            });
            browserNotify(payload);
        });

        refresh();

        return { state, refresh, openAlerts };
    },
};

registry.category("services").add("reorder_alert", reorderAlertService);
