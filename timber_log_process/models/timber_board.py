import math
from odoo import api, fields, models
from odoo.exceptions import ValidationError

class TimberBoard(models.Model):
    _name = 'timber.board'
    _description = 'Individual Timber Board'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='Board Reference', required=True, copy=False, readonly=True, default=lambda self: self.env['ir.sequence'].next_by_code('timber.board'))
    processing_id = fields.Many2one('timber.processing', string='Source Sawing', required=True, ondelete='cascade', tracking=True)
    log_id = fields.Many2one('timber.log', string='Source Log', related='processing_id.log_id', store=True, readonly=True)
    
    # Vipimo vikiwa katika Inches kama ilivyo kwenye fomula
    width = fields.Float(string='Width (Inch)', required=True, digits=(16, 3))
    thickness = fields.Float(string='Thickness (Inch)', required=True, digits=(16, 3))
    length = fields.Float(string='Length (Inch)', required=True, digits=(16, 2))
    
    cbm = fields.Float(string='Board CBM', compute='_compute_board_cbm', store=True, digits=(16, 6))
    
    status = fields.Selection([
        ('available', 'Available in Stock'),
        ('reserved', 'Reserved'),
        ('sold', 'Sold / Delivered'),
        ('damaged', 'Damaged / Waste')
    ], string='Status', default='available', tracking=True)
    
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', tracking=True)
    
    # Kuunganisha na Odoo Standard Sale Order Line
    sale_order_line_id = fields.Many2one('sale.order.line', string='Sale Order Line', copy=False, tracking=True)

    @api.depends('width', 'thickness', 'length')
    def _compute_board_cbm(self):
        for rec in self:
            if rec.width and rec.thickness and rec.length:
                rec.cbm = (rec.width * rec.thickness * rec.length) / 61023.744
            else:
                rec.cbm = 0.0

    # --- KANUNI YA KUZUIA BOARD CBM ISIZIDI MANUFACTURED CBM ---
    @api.constrains('cbm', 'processing_id')
    def _check_board_cbm_limit(self):
        for board in self:
            if board.processing_id:
                rec = board.processing_id
                board_pct = float(rec.env['ir.config_parameter'].sudo().get_param('timber.board_percentage', 60.0))
                total_expected_output = rec.input_cbm * (board_pct / 100.0)
                
                # Jumla ya bodi zote chini ya sawing order hii
                total_boards_cbm = sum(rec.board_ids.mapped('cbm'))
                
                if total_boards_cbm > total_expected_output:
                    raise ValidationError(
                        f"⚠️ Insufficient Manufactured CBM / Limit Exceeded!\n\n"
                        f"The total CBM of the boards ({total_boards_cbm:.4f} CBM) has exceeded "
                        f"the allowed Manufactured CBM limit ({total_expected_output:.4f} CBM - {board_pct}% of the log).\n"
                        f"Please reduce the size or quantity of the boards."
                    )

    def action_mark_as_sold(self):
        """Kazi ya kubadilisha hali ya bodi kuwa imeuwa na CBM kupungua kwenye stock inayopatikana"""
        for rec in self:
            rec.status = 'sold'

    @api.model
    def mark_boards_as_sold_by_sale(self, sale_order):
        """Inatafuta bodi zilizounganishwa na Sale Order hii na kuzibadilisha kuwa sold"""
        boards = self.search([('sale_order_line_id.order_id', '=', sale_order.id), ('status', '=', 'available')])
        if boards:
            boards.write({'status': 'sold'})


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for order in self:
            # Inaita kazi ya kubadilisha bodi kuwa sold oda inapothibitishwa
            self.env['timber.board'].mark_boards_as_sold_by_sale(order)
        return res