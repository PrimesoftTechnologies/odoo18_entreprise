/** @odoo-module */

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

const EPSILON = 0.000001;

patch(PosStore.prototype, {
    /**
     * Quantity of a product already present in not-yet-finalized orders.
     */
    _getReservedQty(productId) {
        let total = 0;
        for (const order of this.models["pos.order"].getAll()) {
            if (order.finalized) {
                continue;
            }
            for (const line of order.lines) {
                if (line.product_id?.id === productId && !line.refunded_orderline_id) {
                    total += line.qty;
                }
            }
        }
        return total;
    },

    _getUnsyncedProductIds() {
        const ids = new Set();
        for (const order of this.models["pos.order"].getAll()) {
            if (order.finalized) {
                continue;
            }
            for (const line of order.lines) {
                if (line.product_id?.id) {
                    ids.add(line.product_id.id);
                }
            }
        }
        return [...ids];
    },

    async refreshStockQty(productIds) {
        if (!productIds.length) {
            return;
        }
        try {
            const result = await this.data.call("product.product", "get_pos_stock_qty", [
                this.config.id,
                productIds,
            ]);
            for (const [id, qty] of Object.entries(result || {})) {
                const product = this.models["product.product"].get(parseInt(id));
                if (product) {
                    product.pos_qty_available = qty;
                }
            }
        } catch (error) {
            // Offline or server error: keep the quantities we already have.
            console.warn("pos_restriction_quantity: could not refresh stock", error);
        }
    },

    async syncAllOrders() {
        const productIds = this._getUnsyncedProductIds();
        const result = await super.syncAllOrders(...arguments);
        await this.refreshStockQty(productIds);
        return result;
    },

    async addLineToOrder(vals, order, opts = {}, configure = true) {
        let product = vals?.product_id;
        if (product && typeof product !== "object") {
            product = this.models["product.product"].get(product);
        }
        const requestedQty = vals?.qty ?? 1;
        const isRefund = requestedQty < 0 || vals?.refunded_orderline_id;

        if (product && product.is_storable && !isRefund) {
            const onHand = product.pos_qty_available || 0;
            const reserved = this._getReservedQty(product.id);
            const available = onHand - reserved;

            if (onHand <= EPSILON || available < requestedQty - EPSILON) {
                const dialog = this.dialog || this.env.services.dialog;
                const body =
                    onHand <= EPSILON
                        ? _t("'%s' is out of stock (On Hand: 0). You can not sell it.", product.display_name)
                        : _t(
                              "Not enough stock for '%(name)s'. On Hand: %(onhand)s, already in orders: %(reserved)s.",
                              {
                                  name: product.display_name,
                                  onhand: onHand,
                                  reserved: reserved,
                              }
                          );
                dialog.add(AlertDialog, {
                    title: _t("Out of stock"),
                    body,
                });
                return;
            }
        }
        return super.addLineToOrder(...arguments);
    },
});
