/** @odoo-module */

import { Component, onMounted, useRef, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";

const EPSILON = 0.005;

/**
 * Small dialog where the cashier types the ACTUAL selling price of the selected line.
 * The Limit Discount of the product is checked once, when the cashier presses Ok.
 */
export class DiscountPriceDialog extends Component {
    static template = "pos_restriction_quantity.DiscountPriceDialog";
    static components = { Dialog };
    static props = {
        title: String,
        startingValue: { type: Number, optional: true },
        currentLabel: { type: String, optional: true },
        limit: { type: Number, optional: true },
        limitLabel: { type: String, optional: true },
        // called with the typed price when it is valid
        onConfirm: Function,
        close: Function,
        getPayload: { type: Function, optional: true },
    };

    setup() {
        this.inputRef = useRef("input");
        this.state = useState({
            value: this.props.startingValue ? String(this.props.startingValue) : "",
            error: "",
        });
        onMounted(() => {
            const el = this.inputRef.el;
            if (el) {
                el.focus();
                el.select();
            }
        });
    }

    onKeydown(ev) {
        if (ev.key === "Enter") {
            this.onConfirm();
        }
    }

    onConfirm() {
        const typed = parseFloat(String(this.state.value).replace(",", "."));
        if (isNaN(typed) || typed <= 0) {
            this.state.error = _t("Please type a valid price.");
            return;
        }
        const limit = this.props.limit || 0;
        if (limit > 0 && typed < limit - EPSILON) {
            this.state.error = _t("You can not sell below %(limit)s.", {
                limit: this.props.limitLabel || limit,
            });
            return;
        }
        this.props.onConfirm(typed);
        this.props.close();
    }
}
