from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    timber_measurement_ids = fields.One2many(
        "timber.measurement", "picking_id", string="Log Measurements",
        domain=[("kind", "=", "log")])
    timber_total_cbm = fields.Float(
        string="Total Log CBM", compute="_compute_timber_total_cbm",
        store=True, digits=(16, 6))

    # ---- Transit Pass (TP) --------------------------------------------
    tp_number = fields.Char(string="TP Number", tracking=True)
    tp_office_seal = fields.Char(string="Office of the (Seal)")
    tp_number_ref = fields.Char(string="Number")
    tp_date = fields.Date(string="Date")
    tp_due_date = fields.Date(string="Due Date")
    tp_purchaser = fields.Char(string="Purchaser Name")
    tp_licence_type = fields.Char(string="Type of Licence")
    tp_transport_mode = fields.Selection(
        [("road", "Road"), ("air", "Air"), ("water", "Water")],
        string="Mode of Transport", default="road")
    tp_vehicle_no = fields.Char(string="Vehicle Number")
    tp_estimated_distance = fields.Char(string="Estimated Distance")
    tp_expired_date = fields.Date(string="Expired Date")
    tp_registration_no = fields.Char(string="Registration Number")
    tp_produce_desc = fields.Char(string="Description of Forest Produced")
    tp_species_size = fields.Char(string="Species and Size of Individual logs")
    tp_quantity = fields.Char(string="Quantity")
    tp_forest_origin = fields.Char(string="Name of Forest (town of origin)")
    tp_town_district = fields.Char(string="Name town/district")
    tp_marker_name = fields.Char(string="Marker Name")
    tp_designation = fields.Char(string="Designation")
    tp_station = fields.Char(string="Station")
    tp_indicator_a = fields.Char(string="Indicator A")

    @api.depends("timber_measurement_ids.cbm")
    def _compute_timber_total_cbm(self):
        for picking in self:
            picking.timber_total_cbm = sum(picking.timber_measurement_ids.mapped("cbm"))

    def action_timber_generate_lots(self):
        """Create one standard Lot per measured log and put its CBM as the
        done quantity on the standard receipt line."""
        cbm_uom = self.env.ref("uom.product_uom_cubic_meter")
        for picking in self:
            if picking.state in ("done", "cancel"):
                raise UserError(_("This receipt is already closed."))
            move = picking.move_ids.filtered(
                lambda m: m.product_id.timber_type == "log")[:1]
            if not move:
                raise UserError(_(
                    "Add a product with Timber Role = Timber Log on the "
                    "Operations tab (or on the Purchase Order) first."))
            if move.product_id.tracking != "lot":
                raise UserError(_(
                    "The log product must be tracked By Lots in its Inventory tab."))
            lines = picking.timber_measurement_ids.filtered(
                lambda l: not l.lot_id and l.cbm > 0)
            if not lines:
                raise UserError(_("There are no new measurement lines with a CBM to process."))
            if picking.state == "draft":
                picking.action_confirm()
                move = picking.move_ids.filtered(
                    lambda m: m.product_id.timber_type == "log")[:1]

            # drop empty, un-lotted suggestion lines created by Odoo
            move.move_line_ids.filtered(
                lambda ml: not ml.lot_id and not ml.lot_name).unlink()

            for line in lines:
                lot = self.env["stock.lot"].create({
                    "name": line.name,
                    "product_id": move.product_id.id,
                    "company_id": picking.company_id.id,
                    "timber_circumference": line.circumference,
                    "timber_log_length": line.length,
                })
                line.lot_id = lot
                move.write({"move_line_ids": [Command.create({
                    "product_id": move.product_id.id,
                    "lot_id": lot.id,
                    "quantity": cbm_uom._compute_quantity(line.cbm, move.product_uom),
                    "product_uom_id": move.product_uom.id,
                    "location_id": move.location_id.id,
                    "location_dest_id": move.location_dest_id.id,
                    "picking_id": picking.id,
                })]})
        return True
