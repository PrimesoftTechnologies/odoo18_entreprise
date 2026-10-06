from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError


class ClearanceRecord(models.Model):
    """
    Adds role checks and email notifications to clearance actions.
    Inherits clearance.record defined in clearing_order.py.
    """
    _inherit = 'clearance.record'

    def _send_template(self, xml_id):
        template = self.env.ref(xml_id, raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)

    def _is_officer(self):
        return self.env.user.has_group('sas_logistics.group_sas_officer')

    def _is_manager(self):
        return self.env.user.has_group('sas_logistics.group_sas_manager')

    def _is_admin(self):
        return self.env.user.has_group('sas_logistics.group_sas_administrator')

    def action_start(self):
        """Officer starts clearing. Notifies responsible officer by email."""
        for rec in self:
            if not (rec._is_officer() or rec._is_manager() or rec._is_admin()):
                raise AccessError(_("Only an Officer or above can start the clearing process."))
        super().action_start()
        for rec in self:
            rec._send_template('sas_logistics.email_template_clearing_started')

    def action_complete(self):
        """
        Officer completes clearing.
        Calls parent (which calls shipping_order.action_cleared).
        Sends completion email to CRO and Manager.
        """
        for rec in self:
            if not (rec._is_officer() or rec._is_manager() or rec._is_admin()):
                raise AccessError(_("Only an Officer or above can complete the clearing process."))
        super().action_complete()
        for rec in self:
            rec._send_template('sas_logistics.email_template_clearance_completed')

    def action_cancel(self):
        for rec in self:
            if not (rec._is_officer() or rec._is_manager() or rec._is_admin()):
                raise AccessError(_("Only an Officer or above can cancel a clearance record."))
        super().action_cancel()


class TransportAssignment(models.Model):
    """Adds email notification when transport is confirmed."""
    _inherit = 'transport.assignment'

    def _send_template(self, xml_id):
        template = self.env.ref(xml_id, raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)

    def action_confirm(self):
        """Notify driver and CRO when transport is confirmed."""
        super().action_confirm()
        for rec in self:
            rec._send_template('sas_logistics.email_template_transport_assigned')