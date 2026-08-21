from odoo import models, fields, api
from odoo.exceptions import UserError

class AccountMove(models.Model):
    _inherit = 'account.move'

    state = fields.Selection(
        selection_add=[('eto_approve', 'Wait for Approval')],
        ondelete={'eto_approve': 'cascade'}
    )
    
    is_approver = fields.Boolean(compute="_compute_is_approver")
    
    approved_by_id = fields.Many2one('res.users', string="Approved By", readonly=True, copy=False)
    approved_date = fields.Datetime(string="Approval Date", readonly=True, copy=False)

    def _compute_is_approver(self):
        for move in self:
            move.is_approver = self.env.user in move.company_id.invoice_approver_ids

    def action_post(self):
        """ post """
        for move in self:
            if move.company_id.invoice_approval_required and move.state == 'draft':
                move.write({'state': 'eto_approve'})
                return True 
        
        return super(AccountMove, self).action_post()

    def action_approve_invoice(self):
        """ post """
        for move in self:
            if not self.is_approver:
                raise UserError("Oop! Sorry, you have not right to approve invoice")
            
            move.write({
                'approved_by_id': self.env.user.id,
                'approved_date': fields.Datetime.now()
            })
            
            move.action_post()
        return True