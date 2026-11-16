/** @odoo-module */

import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { DiscountPriceDialog } from "@pos_restriction_quantity/app/dialog/discount_price_dialog";

const proto = ProductScreen.prototype;

function toNumber(value) {
    const n = parseFloat(value);
    return isNaN(n) ? 0 : n;
}

function money(pos, amount) {
    try {
        return pos.env.utils.formatCurrency(amount);
    } catch {
        return String(amount);
    }
}

function currentOrder(pos) {
    return (
        (pos.getOrder && pos.getOrder()) ||
        (pos.get_order && pos.get_order()) ||
        pos.selectedOrder ||
        null
    );
}

function selectedLine(order) {
    if (!order) {
        return null;
    }
    return (
        (order.getSelectedOrderline && order.getSelectedOrderline()) ||
        (order.get_selected_orderline && order.get_selected_orderline()) ||
        null
    );
}

// The "%" numpad button takes the actual selling price, so rename it.
if (typeof proto.getNumpadButtons === "function") {
    patch(proto, {
        getNumpadButtons() {
            const buttons = super.getNumpadButtons(...arguments);
            return buttons.map((button) =>
                button.value === "discount" ? { ...button, text: _t("Disc. Price") } : button
            );
        },
    });
}

// "Disc. Price" and "Price" open a small dialog where the cashier types the selling price.
// The Limit Discount is checked once on Ok (not after every key press).
if (typeof proto.onNumpadClick === "function") {
    patch(proto, {
        onNumpadClick(buttonValue) {
            if (buttonValue === "discount" || buttonValue === "price") {
                const line = selectedLine(currentOrder(this.pos));
                if (line) {
                    const dialog = this.dialog || this.pos.dialog || this.env.services.dialog;
                    const original = toNumber(line.price_unit);
                    const effective = original * (1 - toNumber(line.discount) / 100);
                    const isRefund = line.refunded_orderline_id || line.qty < 0;
                    const limit = isRefund ? 0 : toNumber(line.product_id?.pos_discount_limit);
                    dialog.add(DiscountPriceDialog, {
                        title: buttonValue === "discount" ? _t("Disc. Price") : _t("Price"),
                        startingValue: effective,
                        currentLabel: money(this.pos, effective),
                        limit,
                        limitLabel: limit > 0 ? money(this.pos, limit) : "",
                        onConfirm: (typed) => {
                            if (buttonValue === "discount") {
                                // Keep the original price and store the difference as a discount.
                                const percent =
                                    original && typed < original
                                        ? ((original - typed) / original) * 100
                                        : 0;
                                const setDiscount = line.setDiscount || line.set_discount;
                                setDiscount.call(line, percent);
                            } else {
                                line.price_type = "manual";
                                const setPrice = line.setUnitPrice || line.set_unit_price;
                                setPrice.call(line, typed);
                            }
                        },
                    });
                    return;
                }
            }
            return super.onNumpadClick(...arguments);
        },
    });
}
