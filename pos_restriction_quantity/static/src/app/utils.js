/** @odoo-module */

// Keeps a reference to the PosStore so that model patches (order lines),
// which have no access to services, can show dialogs.
let posStore = null;

export function setPosStore(store) {
    posStore = store;
}

export function getPosStore() {
    return posStore;
}
