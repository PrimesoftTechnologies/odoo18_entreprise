/** @odoo-module **/

import { ProductCard } from "@point_of_sale/app/generic_components/product_card/product_card";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(ProductCard.prototype, {
    async onClick() {
        const product = this.props.product;
        // Check if on hand quantity is 0 or less
        const qty = product ? (product.qty_available || 0) : 0;
        
        if (qty <= 0) {
            const popup = this.env.services.popup || this.env.services.dialog;
            if (this.env.services.popup) {
                await this.env.services.popup.add(ErrorPopup, {
                    title: _t("Hakuna Akiba (Out of Stock)"),
                    body: _t("Huwezi kuchagua bidhaa '%s' kwa sababu akiba yake ipo 0. Tafadhali ongeza akiba ya bidhaa (product quantity) kwanza.", product.display_name || product.name),
                });
            } else {
                alert(_t("Huwezi kuchagua bidhaa hii kwa sababu akiba yake ipo 0 au chini ya hapo. Tafadhali ongeza akiba (product quantity) kwanza."));
            }
            return;
        }
        
        return super.onClick(...arguments);
    }
});
