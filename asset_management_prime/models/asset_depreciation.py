import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AssetDepreciationLine(models.Model):
    _name = 'asset.depreciation.line'
    _description = 'Asset Depreciation Line'
    _order = 'asset_id, sequence'

    asset_id = fields.Many2one('asset.asset', required=True, ondelete='cascade', index=True)
    category_id = fields.Many2one(related='asset_id.category_id', store=True)
    company_id = fields.Many2one(related='asset_id.company_id', store=True, index=True)
    currency_id = fields.Many2one(related='asset_id.currency_id', store=True)
    sequence = fields.Integer(default=1)
    name = fields.Char(compute='_compute_name', store=True)
    date = fields.Date('Depreciation Date', required=True, index=True)
    amount = fields.Monetary(required=True, currency_field='currency_id')
    depreciated_value = fields.Monetary('Cumulative Depreciation', compute='_compute_values',
                                        currency_field='currency_id')
    remaining_value = fields.Monetary('Remaining Value', compute='_compute_values',
                                      currency_field='currency_id')
    state = fields.Selection([('draft', 'Draft'), ('posted', 'Posted')], default='draft',
                             required=True, index=True)
    move_id = fields.Many2one('account.move', string='Journal Entry', readonly=True, copy=False)

    @api.depends('asset_id.name', 'sequence')
    def _compute_name(self):
        for line in self:
            line.name = '%s - %s' % (line.asset_id.display_name or '', line.sequence)

    @api.depends('asset_id.purchase_value', 'asset_id.depreciation_line_ids.amount', 'sequence')
    def _compute_values(self):
        for line in self:
            lines = line.asset_id.depreciation_line_ids.filtered(lambda l: l.sequence <= line.sequence)
            line.depreciated_value = sum(lines.mapped('amount'))
            line.remaining_value = line.asset_id.purchase_value - line.depreciated_value

    @api.ondelete(at_uninstall=False)
    def _unlink_except_posted(self):
        if any(l.state == 'posted' for l in self):
            raise UserError(self.env._("You cannot delete a posted depreciation line."))

    def action_post(self):
        for line in self.sorted(lambda l: (l.asset_id.id, l.sequence)):
            if line.state != 'draft':
                continue
            asset = line.asset_id
            cat = asset.category_id
            if not (cat.journal_id and cat.account_depreciation_id and cat.account_expense_id):
                raise UserError(self.env._(
                    "Category '%s' needs a journal, a depreciation account and an expense account.",
                    cat.display_name))
            ref = self.env._("Depreciation %s", asset.display_name)
            move = self.env['account.move'].create({
                'move_type': 'entry',
                'date': line.date,
                'journal_id': cat.journal_id.id,
                'company_id': asset.company_id.id,
                'ref': ref,
                'line_ids': [
                    (0, 0, {'name': ref, 'account_id': cat.account_expense_id.id,
                            'debit': line.amount, 'credit': 0.0}),
                    (0, 0, {'name': ref, 'account_id': cat.account_depreciation_id.id,
                            'debit': 0.0, 'credit': line.amount}),
                ],
            })
            move.action_post()
            line.write({'move_id': move.id, 'state': 'posted'})
            asset.message_post(body=self.env._(
                "Depreciation of %(amount)s posted for %(date)s.",
                amount=line.amount, date=line.date))

    @api.model
    def _cron_post_due_lines(self):
        today = fields.Date.context_today(self)
        lines = self.search([
            ('state', '=', 'draft'), ('date', '<=', today),
            ('asset_id.state', 'in', ('available', 'in_use', 'maintenance')),
            ('category_id.auto_post', '=', True)], order='asset_id, sequence')
        for line in lines:
            try:
                with self.env.cr.savepoint():
                    line.action_post()
            except Exception:
                _logger.exception("Could not post depreciation line %s", line.id)
