/** @odoo-module */

import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

const proto = ProductScreen.prototype;

// Rename the "%" numpad button: it now takes the actual selling price, not a percentage.
// (The conversion to Odoo's internal discount % is done in models/pos_order_line.js)
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
