/** @odoo-module */

import { Component, onMounted, useRef, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";

const EPSILON = 0.005;

/**
 * Dialog where the cashier types, for the selected line:
 *  - mode "discount": the discount AMOUNT taken off the line total (e.g. 5000)
 *  - mode "price":    the new TOTAL price of the line
 * The product's Limit Discount (minimum price) is checked once, when pressing Ok.
 */
export class DiscountPriceDialog extends Component {
    static template = "pos_restriction_quantity.DiscountPriceDialog";
    static components = { Dialog };
    static props = {
        title: String,
        mode: String, // "discount" | "price"
        startingValue: { type: Number, optional: true },
        qtyLabel: { type: String, optional: true },
        originalTotal: Number,
        originalLabel: { type: String, optional: true },
        limit: { type: Number, optional: true }, // minimum allowed total of the line (0 = none)
        limitLabel: { type: String, optional: true },
        maxDiscountLabel: { type: String, optional: true },
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

    get placeholder() {
        return this.props.mode === "discount"
            ? _t("Type the discount amount")
            : _t("Type the total price");
    }

    onKeydown(ev) {
        if (ev.key === "Enter") {
            this.onConfirm();
        }
    }

    onConfirm() {
        const typed = parseFloat(String(this.state.value).replace(",", "."));
        const { mode, originalTotal, limit } = this.props;
        const minimum = limit || 0;

        if (isNaN(typed) || typed < 0 || (mode === "price" && typed <= 0)) {
            this.state.error = _t("Please type a valid amount.");
            return;
        }

        if (mode === "discount") {
            if (typed > originalTotal + EPSILON) {
                this.state.error = _t("The discount can not be more than the line total.");
                return;
            }
            const result = originalTotal - typed;
            if (minimum > 0 && result < minimum - EPSILON) {
                this.state.error = _t(
                    "Discount too big. The most you can give is %(max)s (the total can not go below %(limit)s).",
                    {
                        max: this.props.maxDiscountLabel || originalTotal - minimum,
                        limit: this.props.limitLabel || minimum,
                    }
                );
                return;
            }
        } else if (minimum > 0 && typed < minimum - EPSILON) {
            this.state.error = _t("You can not sell below %(limit)s.", {
                limit: this.props.limitLabel || minimum,
            });
            return;
        }

        this.props.onConfirm(typed);
        this.props.close();
    }
}