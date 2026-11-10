from odoo import api, models


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    @api.model
    def default_get(self, fields_list):
        # Runs when the Credit Note button is clicked and the wizard opens
        ctx = self.env.context
        if ctx.get('active_model') == 'account.move' and ctx.get('active_ids'):
            self.env['account.move'].browse(ctx['active_ids'])._check_credit_note_attachments()
        return super().default_get(fields_list)

    def reverse_moves(self, is_modify=False):
        self.move_ids._check_credit_note_attachments()
        return super().reverse_moves(is_modify=is_modify)
