/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

const BELL_URL = "/hill_location_owner/static/src/sounds/approval_bell.wav";
const BUS_EVENT = "hill_location_owner/pending_approval";
const UNLOCK_EVENTS = ["pointerdown", "keydown", "touchstart"];
const BELL_VOLUME = 0.35; // 0 (silent) .. 1 (full); the sound file itself is already soft

/**
 * Rings a bell + shows a sticky notification when the current user has a transfer
 * waiting for HIS approval:
 *  - once when the web client loads (i.e. right after login)
 *  - live, whenever a new approval request reaches him through the bus
 */
export const approvalBellService = {
    dependencies: ["bus_service", "notification", "orm", "action"],

    start(env, { bus_service, notification, orm, action }) {
        const announced = new Set();
        let checkedAtStart = false;

        function ring() {
            const audio = new Audio(BELL_URL);
            audio.volume = BELL_VOLUME;
            audio.play().catch(() => {
                // Browsers may block sound until the user interacts with the page:
                // ring on the very first click / key press / tap instead.
                const unlock = () => {
                    UNLOCK_EVENTS.forEach((e) => window.removeEventListener(e, unlock, true));
                    audio.play().catch(() => {});
                };
                UNLOCK_EVENTS.forEach((e) => window.addEventListener(e, unlock, true));
            });
        }

        function openApprovals(ids) {
            if (ids.length === 1) {
                return action.doAction({
                    type: "ir.actions.act_window",
                    res_model: "stock.picking",
                    res_id: ids[0],
                    views: [[false, "form"]],
                    target: "current",
                });
            }
            return action.doAction({
                type: "ir.actions.act_window",
                name: _t("Pending Approvals"),
                res_model: "stock.picking",
                views: [[false, "list"], [false, "form"]],
                domain: [["id", "in", ids]],
                target: "current",
            });
        }

        function announce(items) {
            const fresh = items.filter((item) => item.id && !announced.has(item.id));
            if (!fresh.length) {
                return;
            }
            fresh.forEach((item) => announced.add(item.id));
            const ids = fresh.map((item) => item.id);
            let closeNotification;
            closeNotification = notification.add(
                _t("Waiting for your approval: %s", fresh.map((item) => item.name).join(", ")),
                {
                    title: _t("Approval needed"),
                    type: "warning",
                    sticky: true,
                    buttons: [
                        {
                            name: _t("Open"),
                            primary: true,
                            onClick: async () => {
                                if (closeNotification) {
                                    closeNotification();
                                }
                                try {
                                    // opening it = seen: remove MY to-do activity for these transfers
                                    await orm.call("stock.picking", "acknowledge_pending_approvals", [ids]);
                                } catch {
                                    // never block opening the transfer
                                }
                                await openApprovals(ids);
                            },
                        },
                    ],
                }
            );
            ring();
        }

        async function checkPending() {
            if (checkedAtStart) {
                return;
            }
            checkedAtStart = true;
            try {
                const items = await orm.call("stock.picking", "get_my_pending_approvals", []);
                announce(items);
            } catch {
                // user without Inventory access: nothing to approve
            }
        }

        env.bus.addEventListener("WEB_CLIENT_READY", checkPending);
        setTimeout(checkPending, 5000); // safety net if the event was missed

        bus_service.subscribe(BUS_EVENT, (payload) => {
            announce([{ id: payload.picking_id, name: payload.name }]);
        });
    },
};

registry.category("services").add("hill_approval_bell", approvalBellService);
