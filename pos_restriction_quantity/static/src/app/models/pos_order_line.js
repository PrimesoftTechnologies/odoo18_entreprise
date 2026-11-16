/** @odoo-module */

import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { getPosStore } from "@pos_restriction_quantity/app/utils";

const EPSILON = 0.005;

function toNumber(value) {
    const n = parseFloat(value);
    return isNaN(n) ? 0 : n;
}

function formatMoney(pos, amount) {
    try {
        return pos.env.utils.formatCurrency(amount);
    } catch {
        return String(amount);
    }
}

/**
 * When the cashier uses the discount button of the numpad, the typed number is the
 * ACTUAL SELLING PRICE per unit (e.g. 70000), not a percentage.
 * Convert it to the percentage Odoo stores internally, so the original price and the
 * discount are both still visible on the line / receipt.
 * Empty or 0 resets the discount.
 */
function priceToPercent(line, typedPrice) {
    const original = toNumber(line.price_unit);
    const typed = toNumber(typedPrice);
    if (!original || !typed || typed >= original) {
        return 0;
    }
    return Math.min(((original - typed) / original) * 100, 100);
}

function resolveDiscount(line, discount) {
    const pos = getPosStore();
    if (pos && pos._discountAmountMode) {
        return priceToPercent(line, discount);
    }
    return toNumber(discount);
}

/**
 * Returns true when selling `line` at `price` with `discount` % is below the
 * product's Limit Discount. Shows a dialog in that case.
 */
function violatesLimit(line, price, discount) {
    const product = line.product_id;
    const limit = product && product.pos_discount_limit;
    if (!limit || limit <= 0) {
        return false;
    }
    // Ignore automatic price changes (pricelist recomputation), only guard cashier actions.
    if (line.price_type === "automatic") {
        return false;
    }
    // Refund lines are not restricted.
    if (line.refunded_orderline_id || line.qty < 0) {
        return false;
    }
    const effective = price * (1 - discount / 100);
    if (effective >= limit - EPSILON) {
        return false;
    }
    const pos = getPosStore();
    if (pos) {
        const dialog = pos.dialog || pos.env.services.dialog;
        dialog.add(AlertDialog, {
            title: _t("Price below limit"),
            body: _t(
                "You can not sell '%(name)s' below %(limit)s. The price you tried is %(price)s.",
                {
                    name: product.display_name,
                    limit: formatMoney(pos, limit),
                    price: formatMoney(pos, effective),
                }
            ),
        });
        try {
            pos.numberBuffer?.reset?.();
        } catch {
            // ignore
        }
    }
    return true;
}

const proto = PosOrderline.prototype;

// Method names differ between snake_case and camelCase builds: patch what exists.
if (typeof proto.set_unit_price === "function") {
    patch(proto, {
        set_unit_price(price) {
            if (violatesLimit(this, toNumber(price), toNumber(this.discount))) {
                return;
            }
            return super.set_unit_price(...arguments);
        },
    });
}
if (typeof proto.setUnitPrice === "function") {
    patch(proto, {
        setUnitPrice(price) {
            if (violatesLimit(this, toNumber(price), toNumber(this.discount))) {
                return;
            }
            return super.setUnitPrice(...arguments);
        },
    });
}
if (typeof proto.set_discount === "function") {
    patch(proto, {
        set_discount(discount) {
            const percent = resolveDiscount(this, discount);
            if (violatesLimit(this, toNumber(this.price_unit), percent)) {
                return;
            }
            return super.set_discount(percent);
        },
    });
}
if (typeof proto.setDiscount === "function") {
    patch(proto, {
        setDiscount(discount) {
            const percent = resolveDiscount(this, discount);
            if (violatesLimit(this, toNumber(this.price_unit), percent)) {
                return;
            }
            return super.setDiscount(percent);
        },
    });
}
