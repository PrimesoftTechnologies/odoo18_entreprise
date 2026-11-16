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
                button.value === "discount" ? { ...button, text: _t("Discount") } : button
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
                    const qty = Math.abs(toNumber(line.qty)) || 1;
                    const originalTotal = toNumber(line.price_unit) * qty;
                    const effectiveTotal = originalTotal * (1 - toNumber(line.discount) / 100);
                    const isRefund = line.refunded_orderline_id || line.qty < 0;
                    const unitLimit = isRefund ? 0 : toNumber(line.product_id?.pos_discount_limit);
                    const limitTotal = unitLimit * qty;
                    const isDiscount = buttonValue === "discount";
                    dialog.add(DiscountPriceDialog, {
                        title: isDiscount ? _t("Discount amount") : _t("Total price"),
                        mode: isDiscount ? "discount" : "price",
                        // discount: amount already given; price: current total
                        startingValue: isDiscount ? originalTotal - effectiveTotal : effectiveTotal,
                        qtyLabel: String(qty),
                        originalTotal,
                        originalLabel: money(this.pos, originalTotal),
                        limit: limitTotal,
                        limitLabel: limitTotal > 0 ? money(this.pos, limitTotal) : "",
                        maxDiscountLabel:
                            limitTotal > 0 ? money(this.pos, originalTotal - limitTotal) : "",
                        onConfirm: (typed) => {
                            if (isDiscount) {
                                // typed = amount taken off the line total. Odoo stores a %.
                                const percent = originalTotal ? (typed / originalTotal) * 100 : 0;
                                const setDiscount = line.setDiscount || line.set_discount;
                                setDiscount.call(line, percent);
                            } else {
                                // "Price" changes the unit price: total / quantity.
                                line.price_type = "manual";
                                const setPrice = line.setUnitPrice || line.set_unit_price;
                                setPrice.call(line, typed / qty);
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