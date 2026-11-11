# -*- coding: utf-8 -*-

from odoo import _, models
from odoo.exceptions import UserError

from .mrp_production import PROD_GROUP


class MrpProductionBackorder(models.TransientModel):
    _inherit = 'mrp.production.backorder'

    def _check_production_manager(self):
        if not self.env.su and not self.env.user.has_group(PROD_GROUP):
            raise UserError(_("Only the Production Manager can decide 'Create Backorder' or 'No Backorder'."))

    def action_close_mo(self):
        self._check_production_manager()
        return super().action_close_mo()

    def action_backorder(self):
        self._check_production_manager()
        return super().action_backorder()
