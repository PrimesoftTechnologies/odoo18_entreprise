# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError

REVIEWER_GROUP = 'helper_sales.group_entry_reviewer'


class AccountMoveReview(models.Model):
    _inherit = 'account.move'

    review_required = fields.Boolean(
        string='Review Required', compute='_compute_review_required', store=True,
        help="Bank entry that contains a manual operation made during bank reconciliation.",
    )
    reviewed = fields.Boolean(string='Reviewed', copy=False, readonly=True, tracking=True)
    reviewed_by = fields.Many2one('res.users', string='Reviewed By', copy=False, readonly=True)
    reviewed_date = fields.Datetime(string='Reviewed On', copy=False, readonly=True)

    @api.depends('statement_line_id', 'state', 'line_ids.matching_number', 'line_ids.account_id',
                 'journal_id.default_account_id')
    def _compute_review_required(self):
        for move in self:
            required = False
            if move.statement_line_id and move.state == 'posted':
                journal = move.journal_id
                skipped = journal.default_account_id
                suspense = getattr(journal, 'suspense_account_id', False)
                if suspense:
                    skipped |= suspense
                # a line that is neither the bank line, nor the suspense line, nor matched to another
                # document = a manual operation
                manual = move.line_ids.filtered(
                    lambda l: l.account_id not in skipped and not l.matching_number)
                required = bool(manual)
            move.review_required = required

    def action_review_entry(self):
        if not self.env.user.has_group(REVIEWER_GROUP):
            raise UserError(_("Only a Journal Entry Reviewer can review this entry."))
        for move in self:
            if not move.review_required:
                raise UserError(_("%s does not need a review.", move.display_name))
        self.sudo().write({
            'reviewed': True,
            'reviewed_by': self.env.uid,
            'reviewed_date': fields.Datetime.now(),
        })
        for move in self:
            move.message_post(body=_("Journal entry reviewed by %s.", self.env.user.name))
        return True
