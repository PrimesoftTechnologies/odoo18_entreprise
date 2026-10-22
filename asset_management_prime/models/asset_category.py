from odoo import api, fields, models


class AssetCategory(models.Model):
    _name = 'asset.category'
    _description = 'Asset Category'
    _inherit = ['mail.thread']
    _order = 'name'

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(help="Short code, e.g. IT, FUR, VEH")
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company)

    # Depreciation defaults
    method = fields.Selection([
        ('linear', 'Straight-Line'),
        ('degressive', 'Declining Balance'),
        ('manual', 'Manual / No Depreciation'),
    ], string='Depreciation Method', default='linear', required=True, tracking=True)
    useful_life = fields.Integer('Useful Life (Months)', default=60)
    salvage_percent = fields.Float('Salvage Value (%)', default=0.0)
    degressive_factor = fields.Float('Declining Factor', default=0.3,
                                     help="Yearly rate applied on the book value (0.3 = 30%).")
    auto_post = fields.Boolean(
        'Auto-Post Entries', default=False,
        help="If checked, the daily cron posts due depreciation entries automatically.")

    # Accounting
    journal_id = fields.Many2one('account.journal', string='Asset Journal',
                                 domain="[('type', '=', 'general')]")
    account_asset_id = fields.Many2one('account.account', string='Asset Account')
    account_depreciation_id = fields.Many2one(
        'account.account', string='Accumulated Depreciation Account')
    account_expense_id = fields.Many2one('account.account', string='Depreciation Expense Account')
    account_gain_loss_id = fields.Many2one('account.account', string='Gain/Loss on Disposal Account')

    asset_count = fields.Integer(compute='_compute_asset_count')

    def _compute_asset_count(self):
        data = self.env['asset.asset']._read_group(
            [('category_id', 'in', self.ids)], ['category_id'], ['__count'])
        mapped = {cat.id: count for cat, count in data}
        for rec in self:
            rec.asset_count = mapped.get(rec.id, 0)

    def action_view_assets(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.name,
            'res_model': 'asset.asset',
            'view_mode': 'list,kanban,form',
            'domain': [('category_id', '=', self.id)],
            'context': {'default_category_id': self.id},
        }
