# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.exceptions import AccessError


class ClearanceRecord(models.Model):
    _inherit = 'clearance.record'

    def _check_finance_access(self):
        """Only Administrator or Bookkeeper can access finance actions."""
        user = self.env.user
        if not (
            user.has_group('base.group_system') or              # Administrator
            user.has_group('account.group_account_user')        # Bookkeeper
        ):
            raise AccessError(_(
                "Only Administrators and Bookkeepers can perform "
                "financial actions on Clearance Records."
            ))

    def action_create_reimbursement(self):
        self._check_finance_access()
        return super().action_create_reimbursement()

    def action_create_invoice(self):
        self._check_finance_access()
        return super().action_create_invoice()

    def action_view_expenses(self):
        self._check_finance_access()
        return super().action_view_expenses()

    def action_view_reimbursements(self):
        self._check_finance_access()
        return super().action_view_reimbursements()

    def action_view_invoices(self):
        self._check_finance_access()
        return super().action_view_invoices()