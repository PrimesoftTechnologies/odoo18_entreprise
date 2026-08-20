/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";

patch(PosOrderline.prototype, {

    setEmployee(employee) {
        this.employee_id = employee.id;
        this.employee_name = employee.name;
        this.setDirty();
    },

    getDisplayData() {
        const data = super.getDisplayData(...arguments);

        // Angalia kama tupo kwenye risiti au kama hii inaitwa kwa ajili ya kuprint
        const isReceipt = (this.order && this.order.uiState && this.order.uiState.screen === 'ReceiptScreen') ||
                          document.querySelector('.pos-receipt') !== null ||
                          document.body.classList.contains('print');

        // Kama NI RISITI, USIWEKE jina la employee kwenye customerNote
        if (this.employee_name && !isReceipt) {
            data.customerNote = "👤 " + this.employee_name;
        }

        return data;
    },

    serialize(options = {}) {
        const data = super.serialize(options);
        data.employee_id = this.employee_id || false;
        return data;
    },

    initFromJSON(json) {
        super.initFromJSON(...arguments);
        this.employee_id = json.employee_id || false;
    },

});