from odoo import _, api, fields, models
from odoo.exceptions import UserError


class MrpProduction(models.Model):
    """Sawing = standard Manufacturing Order (logs -> boards + waste by-product)."""
    _inherit = "mrp.production"

    timber_board_ids = fields.One2many(
        "timber.measurement", "production_id", string="Produced Boards",
        domain=[("kind", "=", "board")])
    timber_board_cbm = fields.Float(
        string="Boards CBM (measured)", compute="_compute_timber_board_cbm",
        store=True, digits=(16, 4))
    timber_input_cbm = fields.Float(
        string="Logs Used (CBM)", compute="_compute_timber_cbm", digits=(16, 4))
    timber_waste_cbm = fields.Float(
        string="Waste (CBM)", compute="_compute_timber_cbm", digits=(16, 4))
    timber_yield_pct = fields.Float(
        string="Yield (%)", compute="_compute_timber_cbm", digits=(16, 2))

    @api.depends("timber_board_ids.cbm")
    def _compute_timber_board_cbm(self):
        for mo in self:
            mo.timber_board_cbm = sum(mo.timber_board_ids.mapped("cbm"))

    @api.depends("timber_board_cbm", "move_raw_ids.product_qty",
                 "move_raw_ids.product_id", "move_finished_ids.product_qty",
                 "move_finished_ids.product_id")
    def _compute_timber_cbm(self):
        for mo in self:
            raw = mo.move_raw_ids.filtered(lambda m: m.product_id.timber_type == "log")
            waste = mo.move_finished_ids.filtered(lambda m: m.product_id.timber_type == "waste")
            mo.timber_input_cbm = sum(raw.mapped("product_qty"))
            mo.timber_waste_cbm = sum(waste.mapped("product_qty"))
            mo.timber_yield_pct = (
                mo.timber_board_cbm / mo.timber_input_cbm * 100.0
                if mo.timber_input_cbm else 0.0)

    def action_timber_apply_board_cbm(self):
        """Use the measured boards CBM as the quantity produced."""
        for mo in self:
            if mo.state not in ("confirmed", "progress", "to_close"):
                raise UserError(_("Confirm the Manufacturing Order first."))
            if not mo.timber_board_cbm:
                raise UserError(_("Enter the board measurements first."))
            mo.qty_producing = mo.timber_board_cbm
            if hasattr(mo, "_set_qty_producing"):
                mo._set_qty_producing()
        return True
