/** @odoo-module **/

import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(ProductScreen.prototype, {
    async _clickProduct(product) {
        const qty = product ? (product.qty_available ?? 0) : 0;
        
        if (qty <= 0) {
            // Use notification or dialog service safely without module dependency failure
            if (this.env.services.notification) {
                this.env.services.notification.add(
                    _t("Huwezi kuchagua '%s' kwa sababu akiba (On Hand) ipo 0 au chini ya hapo. Ongeza akiba kwanza.", product.display_name || product.name),
                    { title: _t("Hakuna Akiba (Out of Stock)"), type: "danger" }
                );
            } else if (this.env.services.dialog) {
                alert(_t("Huwezi kuchagua bidhaa hii kwa sababu akiba yake ipo 0. Tafadhali ongeza akiba kwanza."));
            }
            return;
        }
        return super._clickProduct(...arguments);
    }
});
