/** @odoo-module **/

import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";

patch(ProductScreen.prototype, {
    async _clickProduct(product) {
        const qty = product ? (product.qty_available !== undefined ? product.qty_available : 0) : 0;
        
        if (qty <= 0) {
            await this.popup.add(ErrorPopup, {
                title: _t("Hakuna Akiba (Out of Stock)"),
                body: _t("Huwezi kuchagua bidhaa '%s' kwa sababu akiba yake ipo 0 au chini ya hapo. Tafadhali ongeza akiba kwanza.", product.display_name || product.name),
            });
            return;
        }
        return super._clickProduct(...arguments);
    }
});
