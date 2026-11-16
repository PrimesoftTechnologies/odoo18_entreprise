/** @odoo-module */

import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

const proto = ProductScreen.prototype;

// While the cashier types in the numpad's discount mode, the value is an AMOUNT
// (not a %). The flag is read by the order line patch, which converts it to a %.
if (typeof proto.updateSelectedOrderline === "function") {
    patch(proto, {
        async updateSelectedOrderline() {
            const isDiscount = this.pos.numpadMode === "discount";
            if (isDiscount) {
                this.pos._discountAmountMode = true;
            }
            try {
                return await super.updateSelectedOrderline(...arguments);
            } finally {
                this.pos._discountAmountMode = false;
            }
        },
    });
}

// Rename the "%" numpad button so the cashier knows it takes an amount.
if (typeof proto.getNumpadButtons === "function") {
    patch(proto, {
        getNumpadButtons() {
            const buttons = super.getNumpadButtons(...arguments);
            return buttons.map((button) =>
                button.value === "discount" ? { ...button, text: _t("Disc.") } : button
            );
        },
    });
}
