from odoo import api, fields, models
from odoo.exceptions import UserError


class AssetDisposal(models.Model):
    _name = 'asset.disposal'
    _description = 'Asset Disposal'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char('Reference', default='New', copy=False, readonly=True)
    asset_id = fields.Many2one('asset.asset', required=True, tracking=True, index=True,
                               domain="[('state', 'in', ('available', 'in_use', 'maintenance'))]")
    company_id = fields.Many2one('res.company', required=True,
                                 default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id')
    date = fields.Date('Disposal Date', default=fields.Date.context_today, required=True)
    disposal_type = fields.Selection([
        ('sale', 'Sale'), ('scrap', 'Scrap'), ('lost', 'Lost / Stolen'), ('donation', 'Donation')],
        default='scrap', required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Buyer / Recipient')
    sale_value = fields.Monetary('Sale Value', currency_field='currency_id')
    counterpart_account_id = fields.Many2one(
        'account.account', string='Receipt Account',
        help="Bank / receivable account debited with the sale proceeds.")
    reason = fields.Text(required=True)
    book_value = fields.Monetary('Book Value at Disposal', readonly=True, currency_field='currency_id')
    gain_loss = fields.Monetary('Gain / (Loss)', readonly=True, currency_field='currency_id')
    approved_by_id = fields.Many2one('res.users', readonly=True, copy=False)
    move_id = fields.Many2one('account.move', string='Journal Entry', readonly=True, copy=False)
    state = fields.Selection([
        ('draft', 'Draft'), ('submitted', 'Waiting Approval'), ('approved', 'Approved'),
        ('done', 'Disposed'), ('rejected', 'Rejected'), ('cancel', 'Cancelled')],
        default='draft', tracking=True, copy=False, required=True)

    @api.onchange('disposal_type')
    def _onchange_type(self):
        if self.disposal_type != 'sale':
            self.sale_value = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('asset.disposal') or 'New'
        return super().create(vals_list)

    def action_submit(self):
        self.write({'state': 'submitted'})

    def action_approve(self):
        self.write({'state': 'approved', 'approved_by_id': self.env.user.id})

    def action_reject(self):
        self.write({'state': 'rejected'})

    def action_cancel(self):
        self.filtered(lambda d: d.state != 'done').write({'state': 'cancel'})

    def action_set_draft(self):
        self.filtered(lambda d: d.state in ('rejected', 'cancel')).write({'state': 'draft'})

    def action_done(self):
        for rec in self:
            if rec.state != 'approved':
                raise UserError(self.env._("The disposal must be approved first."))
            asset = rec.asset_id
            cat = asset.category_id

            # 1. Stop depreciation: post what is due, drop the rest.
            lines = asset.depreciation_line_ids
            lines.filtered(lambda l: l.state == 'draft' and l.date <= rec.date).action_post()
            lines.filtered(lambda l: l.state == 'draft').unlink()

            accumulated = asset.depreciated_value
            book = asset.book_value
            sale = rec.sale_value if rec.disposal_type == 'sale' else 0.0
            gain_loss = sale - book
            currency = asset.currency_id

            # 2. Accounting entry (only if the category is accounting-enabled)
            move = False
            if cat.journal_id and cat.account_asset_id and cat.account_depreciation_id:
                name = self.env._("Disposal %s", asset.display_name)
                move_lines = []

                def _line(account, debit=0.0, credit=0.0):
                    if currency.is_zero(debit) and currency.is_zero(credit):
                        return
                    move_lines.append((0, 0, {'name': name, 'account_id': account.id,
                                              'debit': debit, 'credit': credit}))

                _line(cat.account_depreciation_id, debit=accumulated)
                if sale:
                    if not rec.counterpart_account_id:
                        raise UserError(self.env._("Select the receipt account for the sale proceeds."))
                    _line(rec.counterpart_account_id, debit=sale)
                if not currency.is_zero(gain_loss):
                    if not cat.account_gain_loss_id:
                        raise UserError(self.env._(
                            "Set a Gain/Loss account on category '%s'.", cat.display_name))
                    if gain_loss < 0:
                        _line(cat.account_gain_loss_id, debit=-gain_loss)
                    else:
                        _line(cat.account_gain_loss_id, credit=gain_loss)
                _line(cat.account_asset_id, credit=asset.purchase_value)

                move = self.env['account.move'].create({
                    'move_type': 'entry', 'date': rec.date, 'journal_id': cat.journal_id.id,
                    'company_id': rec.company_id.id, 'ref': name, 'line_ids': move_lines})
                move.action_post()

            # 3. Close active assignments and the asset itself
            asset.assignment_ids.filtered(lambda a: a.state == 'active').write({
                'state': 'returned', 'date_to': fields.Datetime.now()})
            asset.write({'state': 'disposed', 'employee_id': False})
            asset.message_post(body=self.env._(
                "Asset disposed (%(type)s). Book value %(book)s, gain/(loss) %(gl)s.",
                type=dict(rec._fields['disposal_type'].selection)[rec.disposal_type],
                book=book, gl=gain_loss))
            rec.write({'state': 'done', 'book_value': book, 'gain_loss': gain_loss,
                       'move_id': move.id if move else False})
