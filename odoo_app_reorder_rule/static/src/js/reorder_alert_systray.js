/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class ReorderAlertSystray extends Component {
    static template = "odoo_app_reorder_rule.ReorderAlertSystray";
    static props = {};

    setup() {
        this.service = useService("reorder_alert");
        this.state = useState(this.service.state);
    }

    onClick() {
        this.service.openAlerts();
    }
}

registry.category("systray").add(
    "odoo_app_reorder_rule.ReorderAlertSystray",
    { Component: ReorderAlertSystray },
    { sequence: 20 }
);
