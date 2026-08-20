/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
    },

    async validateOrder(isForceValidate) {
        const order = this.currentOrder;
        
        if (order) {
            // Angalia kama kuna bidhaa yoyote ambayo haina mfanyakazi aliyechaguliwa
            const linesWithoutEmployee = order.get_orderlines().filter(line => !line.employee_id);

            if (linesWithoutEmployee.length > 0) {
                // Tumia AlertDialog ya Odoo 18 kuonyesha ujumbe wa onyo kwa usahihi
                this.dialog.add(AlertDialog, {
                    title: _t('Employee Required'),
                    body: _t('Please select an employee for all items in the order before proceeding to payment!'),
                });
                return; // Zuia malipo yasiendelee
            }
        }

        // Kama kila kitu kiko sawa, ruhusu malipo yaendelee kawaida
        return super.validateOrder(...arguments);
    },
});