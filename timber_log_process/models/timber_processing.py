import math
from odoo import api, fields, models
from odoo.exceptions import ValidationError

class TimberProcessing(models.Model):
    _name = 'timber.processing'
    _description = 'Sawing / Processing Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_processed desc, id desc'

    name = fields.Char(string='Sawing Reference', required=True, copy=False, readonly=True, default=lambda self: self.env['ir.sequence'].next_by_code('timber.processing'))
    log_id = fields.Many2one('timber.log', string='Source Log', required=True)
    date_processed = fields.Date(string='Processing Date', default=fields.Date.today, required=True)
    user_id = fields.Many2one('res.users', string='Responsible Person', default=lambda self: self.env.user)
    
    # Sehemu ya kuchagua kama unataka kuuza kwa CBM au kwa PC
    sale_by = fields.Selection([
        ('cbm', 'Sell by CBM'),
        ('pc', 'Sell by Pieces (PC)')
    ], string='Sales Unit', default='cbm', required=True, help="Chagua kama unataka kuuza kwa ujazo wa CBM au kwa idadi ya vipande (PC)")

    input_cbm = fields.Float(string='Initial Log CBM', related='log_id.total_cbm', store=True, readonly=True, digits=(16, 4))
    
    board_ids = fields.One2many('timber.board', 'processing_id', string='Produced Boards (Optional)')
    
    # Uwanja mpya wa kujumlisha CBM za bodi zote zilizomo kwenye jedwali kwa ajili ya Grand Total Board CBM
    total_board_cbm = fields.Float(string='Grand Total Board CBM', compute='_compute_total_board_cbm', store=True, digits=(16, 4))

    # Output na Waste zinakokotolewa kwa kutoa jumla ya CBM za bodi zilizojazwa
    output_cbm = fields.Float(string='Manufactured CBM', compute='_compute_output_and_waste', store=True, digits=(16, 4))
    waste_cbm = fields.Float(string='Waste Produced CBM', compute='_compute_output_and_waste', store=True, digits=(16, 4))
    waste_percentage = fields.Float(string='Waste Used(%)', compute='_compute_output_and_waste', store=True, digits=(16, 2))
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'Sawing in Progress'),
        ('done', 'Completed'),
        ('cancel', 'Cancelled')
    ], string='Status', default='draft')

    @api.depends('board_ids', 'board_ids.cbm')
    def _compute_total_board_cbm(self):
        for record in self:
            record.total_board_cbm = sum(record.board_ids.mapped('cbm'))

    @api.depends('input_cbm', 'board_ids.cbm')
    def _compute_output_and_waste(self):
        """
        Inakokotoa Manufactured CBM kama salio (balance) kwa kuchukua lengo 
        la asilimia ya gogo na kupunguza jumla ya CBM za bodi zote zilizojazwa chini.
        """
        for rec in self:
            board_pct = float(rec.env['ir.config_parameter'].sudo().get_param('timber.board_percentage', 60.0))
            waste_pct = float(rec.env['ir.config_parameter'].sudo().get_param('timber.waste_percentage', 40.0))

            total_expected_output = rec.input_cbm * (board_pct / 100.0)
            total_boards_cbm = sum(rec.board_ids.mapped('cbm'))

            rec.output_cbm = max(0.0, total_expected_output - total_boards_cbm)
            rec.waste_cbm = rec.input_cbm * (waste_pct / 100.0)
            rec.waste_percentage = waste_pct

    # --- KANUNI YA KUZUIA BODI CBM ISIZIDI KIKOMO CHA MANUFACTURED CBM ---
    @api.constrains('board_ids', 'board_ids.cbm')
    def _check_board_cbm_limit(self):
        for rec in self:
            board_pct = float(rec.env['ir.config_parameter'].sudo().get_param('timber.board_percentage', 60.0))
            total_expected_output = rec.input_cbm * (board_pct / 100.0)
            total_boards_cbm = sum(rec.board_ids.mapped('cbm'))
            
            if total_boards_cbm > total_expected_output:
                raise ValidationError(
                    f"⚠️ Insufficient Manufactured CBM / Limit Exceeded!\n\n"
                    f"Jumla ya CBM za bodi ulizoweka ({total_boards_cbm:.4f} CBM) "
                    f"zimezidi kiwango cha juu kinachoruhusiwa kwa gogo hili ({total_expected_output:.4f} CBM - {board_pct}% ya gogo la mwanzo).\n"
                    f"Tafadhali punguza ukubwa au idadi ya bodi ili zisivuke kikomo cha Manufactured CBM."
                )

    def action_start(self):
        self.state = 'in_progress'
        if self.log_id:
            self.log_id.state = 'processing'

    def action_done(self):
        self.state = 'done'
        if self.log_id:
            self.log_id.state = 'done'

    def action_create_sale_order(self):
        self.ensure_one()
        
        # Kutafuta au kuchagua mteja wa kwanza ili kuzuia error ya partner_id
        default_partner = self.env['res.partner'].search([('customer_rank', '>', 0)], limit=1)
        if not default_partner:
            default_partner = self.env['res.partner'].search([], limit=1)

        product = self.env['product.product'].search([('name', 'ilike', 'Mtiki Timber')], limit=1)
        if not product:
            product = self.env['product.product'].search([], limit=1)

        # Kuchukua jumla halisi ya bodi zilizojazwa chini kwenye table
        total_actual_boards_cbm = sum(self.board_ids.mapped('cbm')) if self.board_ids else 0.0
        total_pieces = len(self.board_ids) if self.board_ids else 0.0

        if self.sale_by == 'pc':
            qty = total_pieces
            line_name = f'Mtiki Timber Production (Total Pieces: {int(total_pieces)})'
        else:
            qty = total_actual_boards_cbm
            line_name = f'Mtiki Timber Production (Actual Boards CBM)'

        sale_line_vals = {
            'product_id': product.id if product else False,
            'name': line_name,
            'product_uom_qty': qty, 
            'price_unit': 0.0, 
        }

        # Kutengeneza Sales Order mpya yenye mstari wa mauzo ya bodi halisi
        sale_order = self.env['sale.order'].create({
            'partner_id': default_partner.id if default_partner else False, 
            'order_line': [(0, 0, sale_line_vals)],
        })

        # Kuunganisha sale order line iliyotengenezwa na bodi zote ili zikiconfirm zibadilishe status
        if sale_order.order_line and self.board_ids:
            line = sale_order.order_line[0]
            self.board_ids.write({'sale_order_line_id': line.id})

        return {
            'type': 'ir.actions.act_window',
            'name': 'Sales Order',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': sale_order.id,
            'target': 'current',
        }