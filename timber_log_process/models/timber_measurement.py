from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class TimberMeasurement(models.Model):
    """Measurement line used on Receipts (logs) and Manufacturing Orders (boards).

    It is only a calculation sheet: the real stock is always handled by
    standard Odoo lots / stock moves.
    """
    _name = "timber.measurement"
    _description = "Timber Measurement Line"
    _order = "id"

    name = fields.Char(string="Reference", copy=False, readonly=True, default="New")
    kind = fields.Selection(
        [("log", "Log"), ("board", "Board")], required=True, default="log")
    picking_id = fields.Many2one("stock.picking", string="Receipt", ondelete="cascade")
    production_id = fields.Many2one(
        "mrp.production", string="Manufacturing Order", ondelete="cascade")
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, readonly=True)

    # Logs (cm)
    circumference = fields.Float(string="Circumference (cm)", digits=(16, 2))
    length = fields.Float(string="Length (cm)", digits=(16, 2))
    # Boards (inch)
    width = fields.Float(string="Width (Inch)", digits=(16, 3))
    thickness = fields.Float(string="Thickness (Inch)", digits=(16, 3))
    board_length = fields.Float(string="Length (Inch)", digits=(16, 2))

    cbm = fields.Float(string="CBM", compute="_compute_cbm", store=True, digits=(16, 6))
    lot_id = fields.Many2one("stock.lot", string="Lot", readonly=True, copy=False)

    @api.depends("kind", "circumference", "length", "width", "thickness", "board_length")
    def _compute_cbm(self):
        for rec in self:
            if rec.kind == "log":
                rec.cbm = ((rec.circumference ** 2) * rec.length / 12566370.0
                           if rec.circumference and rec.length else 0.0)
            else:
                rec.cbm = ((rec.width * rec.thickness * rec.board_length) / 61023.744
                           if rec.width and rec.thickness and rec.board_length else 0.0)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                code = "timber.board" if vals.get("kind") == "board" else "timber.log"
                vals["name"] = self.env["ir.sequence"].next_by_code(code) or "New"
        return super().create(vals_list)

    @api.constrains("cbm", "production_id", "kind")
    def _check_board_cbm_limit(self):
        """Boards cannot exceed the finished quantity planned by the Bill of
        Materials (this replaces the old custom board percentage setting)."""
        for mo in self.filtered(lambda r: r.kind == "board").mapped("production_id"):
            total = sum(mo.timber_board_ids.mapped("cbm"))
            if total - mo.product_qty > 1e-6:
                raise ValidationError(_(
                    "Total board CBM (%(total).4f) is more than the quantity planned "
                    "on %(mo)s (%(planned).4f). The planned quantity comes from the "
                    "Bill of Materials yield.",
                    total=total, mo=mo.name, planned=mo.product_qty))
