from odoo import models, fields, api


class PhoneStockImage(models.Model):
    _name = 'phone.stock.image'
    _description = 'Phone Stock Image'
    _rec_name = 'name'
    _order = 'sequence asc, id asc'

    # =========================================================
    # RELATIONSHIP
    # =========================================================

    phone_id = fields.Many2one(
        'phone.stock',
        string='Phone',
        required=True,
        ondelete='cascade'
    )

    # =========================================================
    # IMAGE DATA
    # =========================================================

    image = fields.Binary(
        string='Image',
        required=True,
        attachment=True
    )

    filename = fields.Char(
        string='Filename'
    )

    name = fields.Char(
        string='Name',
        compute='_compute_name',
        store=True
    )

    # =========================================================
    # ORDER
    # =========================================================

    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Order of images (lower = first)'
    )

    # =========================================================
    # OPTIONAL FIELDS
    # =========================================================

    is_primary = fields.Boolean(
        string='Primary Image',
        default=False,
        help='Mark as the main image for this phone'
    )

    description = fields.Char(
        string='Description'
    )

    # =========================================================
    # COMPUTE: NAME
    # =========================================================

    @api.depends('phone_id.model_name', 'sequence')
    def _compute_name(self):
        for record in self:
            if record.phone_id and record.phone_id.model_name:
                record.name = f"{record.phone_id.model_name} - #{record.sequence}"
            else:
                record.name = "Phone Image"