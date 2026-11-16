/** @odoo-module */

import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { getPosStore } from "@pos_restriction_quantity/app/utils";

const EPSILON = 0.005;

function toNumber(value) {
    const n = parseFloat(String(value ?? "").replace(",", "."));
    return isNaN(n) ? 0 : n;
}

function intDigits(value) {
    return String(Math.floor(Math.abs(toNumber(value)))).length;
}

function formatMoney(pos, amount) {
    try {
        return pos.env.utils.formatCurrency(amount);
    } catch {
        return String(amount);
    }
}

function getNumberBuffer(pos) {
    return pos.numberBuffer || (pos.env && pos.env.services && pos.env.services.number_buffer);
}

/**
 * True when the value comes from the cashier typing on the numpad in the given mode
 * ("price" or "discount"), as opposed to code setting the line programmatically.
 */
function isNumpadInput(pos, mode, typed) {
    if (!pos || pos.numpadMode !== mode) {
        return false;
    }
    try {
        const nb = getNumberBuffer(pos);
        const buffer = nb && typeof nb.get === "function" ? nb.get() : null;
        if (buffer !== null && buffer !== undefined && String(buffer) !== "") {
            return toNumber(buffer) === toNumber(typed);
        }
    } catch {
        // ignore, assume numpad
    }
    return true;
}

/**
 * The numpad discount button takes the ACTUAL SELLING PRICE per unit (e.g. 70000).
 * Odoo stores discounts as a percentage, so convert it. The original price and the
 * discount both stay visible on the line / receipt. Empty or 0 resets the discount.
 */
function priceToPercent(line, typedPrice) {
    const original = toNumber(line.price_unit);
    const typed = toNumber(typedPrice);
    if (!original || !typed || typed >= original) {
        return 0;
    }
    return Math.min(((original - typed) / original) * 100, 100);
}

/**
 * Returns true when the line would be sold below the product's Limit Discount
 * (the change must then be refused).
 *
 * `typedPrice` is only given for numpad input. The numpad applies the number after
 * EVERY key press, so while the cashier is still typing "7", "70", "700"... the value is
 * obviously incomplete: it is refused silently (nothing changes) until the typed number
 * has as many digits as the limit. Only then the "Price below limit" dialog is shown.
 */
function violatesLimit(line, price, discount, typedPrice = null) {
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
    // Still typing (fewer digits than the limit): refuse silently, no popup yet.
    if (typedPrice !== null && intDigits(typedPrice) < intDigits(limit)) {
        return true;
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
            const nb = getNumberBuffer(pos);
            nb && nb.reset && nb.reset();
        } catch {
            // ignore
        }
    }
    return true;
}

function guardedUnitPrice(line, price) {
    const fromNumpad = isNumpadInput(getPosStore(), "price", price);
    return violatesLimit(
        line,
        toNumber(price),
        toNumber(line.discount),
        fromNumpad ? toNumber(price) : null
    );
}

function guardedDiscount(line, discount) {
    const fromNumpad = isNumpadInput(getPosStore(), "discount", discount);
    const percent = fromNumpad ? priceToPercent(line, discount) : toNumber(discount);
    const blocked = violatesLimit(
        line,
        toNumber(line.price_unit),
        percent,
        fromNumpad ? toNumber(discount) : null
    );
    return { blocked, percent };
}

const proto = PosOrderline.prototype;

// Method names differ between snake_case and camelCase builds: patch what exists.
if (typeof proto.set_unit_price === "function") {
    patch(proto, {
        set_unit_price(price) {
            if (guardedUnitPrice(this, price)) {
                return;
            }
            return super.set_unit_price(...arguments);
        },
    });
}
if (typeof proto.setUnitPrice === "function") {
    patch(proto, {
        setUnitPrice(price) {
            if (guardedUnitPrice(this, price)) {
                return;
            }
            return super.setUnitPrice(...arguments);
        },
    });
}
if (typeof proto.set_discount === "function") {
    patch(proto, {
        set_discount(discount) {
            const { blocked, percent } = guardedDiscount(this, discount);
            if (blocked) {
                return;
            }
            return super.set_discount(percent);
        },
    });
}
if (typeof proto.setDiscount === "function") {
    patch(proto, {
        setDiscount(discount) {
            const { blocked, percent } = guardedDiscount(this, discount);
            if (blocked) {
                return;
            }
            return super.setDiscount(percent);
        },
    });
}
