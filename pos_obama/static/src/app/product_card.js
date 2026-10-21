/** @odoo-module */
import { ProductCard } from "@point_of_sale/app/generic_components/product_card/product_card";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(ProductCard.prototype, {
    setup() {
        super.setup(...arguments);
        this.posObama = useService("pos");
    },
    get obamaReference() {
        const product = this.posObama.models["product.product"].get(this.props.productId);
        return product && product.default_code ? product.default_code : "";
    },
});
