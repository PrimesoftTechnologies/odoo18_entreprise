/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(FormController.prototype, {
    async saveButtonClicked(params = {}) {
        if (this.props.resModel === "shipping.order" && !this.model.root.resId) {
            const attachments = document.querySelectorAll(
                ".o-mail-Chatter .o-mail-AttachmentCard"
            );

            if (!attachments.length) {
                this.dialog.add(ConfirmationDialog, {
                    title: "Attachment Required",
                    body: "You must upload at least one attachment before saving this Shipping Order.",
                });
                return;
            }
        }

        return super.saveButtonClicked(params);
    },
});