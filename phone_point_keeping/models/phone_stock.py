from odoo import models, fields, api


class PhoneBrand(models.Model):
    _name = 'phone.brand'
    _description = 'Phone Brand Management'
    _rec_name = 'name'

    name = fields.Char(string='Jina la Brand', required=True)
    category_ids = fields.One2many('phone.category', 'brand_id', string='Categories')


class PhoneCategory(models.Model):
    _name = 'phone.category'
    _description = 'Phone Category Management'
    _rec_name = 'name'

    name = fields.Char(string='Jina la Category (Mf. Galaxy S Series)', required=True)
    brand_id = fields.Many2one('phone.brand', string='Brand', required=True, ondelete='cascade')


class PhoneCondition(models.Model):
    _name = 'phone.condition'
    _description = 'Phone Condition Management'
    _rec_name = 'name'

    name = fields.Char(string='Jina la Condition (Mf. Brand New, UK Used)', required=True)


class PhoneStock(models.Model):
    _name = 'phone.stock'
    _description = 'Phone Stock & IMEI Management'
    _rec_name = 'model_name'

    # =========================================================
    # BASIC INFORMATION
    # =========================================================

    model_name = fields.Char(
        string='Phone Model (e.g. iPhone 13 Pro)',
        required=True
    )

    brand_id = fields.Many2one(
        'phone.brand',
        string='Brand',
        required=True
    )

    category_id = fields.Many2one(
        'phone.category',
        string='Category',
        domain="[('brand_id', '=', brand_id)]",
        required=True
    )

    imei_1 = fields.Char(
        string='IMEI 1',
        required=True,
        index=True
    )

    imei_2 = fields.Char(
        string='IMEI 2 (Optional)'
    )

    serial_number = fields.Char(
        string='Serial Number'
    )

    condition_id = fields.Many2one(
        'phone.condition',
        string='Condition',
        required=True
    )

    # =========================================================
    # FINANCIAL FIELDS
    # =========================================================

    quantity = fields.Integer(
        string='Quantity',
        default=0,
        required=True,
        help='Idadi ya phones kwenye stock'
    )

    buying_price = fields.Float(
        string='Buying Price (TSh) - per piece',
        required=True
    )

    selling_price = fields.Float(
        string='Selling Price (TSh) - per piece',
        required=True
    )

    gross_profit = fields.Float(
        string='Profit per piece (TSh)',
        compute='_compute_profit',
        store=True
    )

    total_buying_price = fields.Float(
        string='Total Buying Price (TSh)',
        compute='_compute_totals',
        store=True
    )

    total_selling_price = fields.Float(
        string='Total Selling Price (TSh)',
        compute='_compute_totals',
        store=True
    )

    total_profit = fields.Float(
        string='Total Profit (TSh)',
        compute='_compute_totals',
        store=True
    )

    # =========================================================
    # SUPPLIER & DATE
    # =========================================================

    supplier_id = fields.Many2one(
        'res.partner',
        string='Supplier'
    )

    date_received = fields.Date(
        string='Date Received',
        default=fields.Date.today
    )

    # =========================================================
    # STATUS — AUTO COMPUTED FROM QUANTITY
    # =========================================================

    status = fields.Selection([
        ('in_stock', 'In Stock'),
        ('out_of_stock', 'Out of Stock'),
    ], string='Status', compute='_compute_status', store=True, readonly=True)

    # =========================================================
    # IMAGES (One2many)
    # =========================================================

    image_ids = fields.One2many(
        'phone.stock.image',
        'phone_id',
        string='Phone Images'
    )

    image_count = fields.Integer(
        string='Images Count',
        compute='_compute_image_count',
        store=True
    )

    primary_image = fields.Binary(
        string='Primary Image',
        compute='_compute_primary_image',
        store=False
    )

    # =========================================================
    # COMPUTE: STATUS (auto-sync na quantity)
    # =========================================================

    @api.depends('quantity')
    def _compute_status(self):
        for record in self:
            if (record.quantity or 0) > 0:
                record.status = 'in_stock'
            else:
                record.status = 'out_of_stock'

    # =========================================================
    # COMPUTE: PROFIT (per piece)
    # =========================================================

    @api.depends('buying_price', 'selling_price')
    def _compute_profit(self):
        for record in self:
            record.gross_profit = record.selling_price - record.buying_price

    # =========================================================
    # COMPUTE: TOTALS (quantity × price)
    # =========================================================

    @api.depends('quantity', 'buying_price', 'selling_price')
    def _compute_totals(self):
        for record in self:
            # ✅ FIX: `or 0` (badala ya `or 1`) — ili quantity=0 iwe 0, si 1
            qty = record.quantity or 0
            record.total_buying_price = qty * (record.buying_price or 0)
            record.total_selling_price = qty * (record.selling_price or 0)
            record.total_profit = record.total_selling_price - record.total_buying_price

    # =========================================================
    # COMPUTE: IMAGE COUNT
    # =========================================================

    @api.depends('image_ids')
    def _compute_image_count(self):
        for record in self:
            record.image_count = len(record.image_ids)

    # =========================================================
    # COMPUTE: PRIMARY IMAGE
    # =========================================================

    @api.depends('image_ids.is_primary', 'image_ids.image')
    def _compute_primary_image(self):
        for record in self:
            primary = record.image_ids.filtered(lambda i: i.is_primary)[:1]
            if not primary:
                primary = record.image_ids[:1]
            record.primary_image = primary.image if primary else False