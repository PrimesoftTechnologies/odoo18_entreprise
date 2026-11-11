# -*- coding: utf-8 -*-

from odoo import fields, models


class MrpProductionRejectWizard(models.TransientModel):
    _name = 'mrp.production.reject.wizard'
    _description = 'Reject Manufacturing Order'

    production_id = fields.Many2one('mrp.production', string='Manufacturing Order', required=True, ondelete='cascade')
    level = fields.Selection([('production', 'Production Manager'), ('cost', 'Cost Shared Manager')], required=True)
    reason = fields.Text(string='Reason for Rejection', required=True)

    def action_confirm_reject(self):
        self.ensure_one()
        self.production_id._do_reject(self.level, self.reason)
        return {'type': 'ir.actions.act_window_close'}
