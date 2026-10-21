/** @odoo-module */
import { ProductCard } from "@point_of_sale/app/components/product_card/product_card";
import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/store/pos_hook";

patch(ProductCard.prototype, {
    setup() {
        super.setup(...arguments);
        this.posObama = usePos();
    },
    get obamaReference() {
        const product = this.posObama.models["product.product"].get(this.props.productId);
        return product && product.default_code ? product.default_code : "";
    },
});
