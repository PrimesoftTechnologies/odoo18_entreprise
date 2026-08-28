from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class FleetVehicle(models.Model):
    _inherit = "fleet.vehicle"

    is_van = fields.Boolean(string="Van Distribution Vehicle", tracking=True)
    van_code = fields.Char(string="Van Code", copy=False, tracking=True)
    
    # Eneo la Stoku la Gari hili (Stock Location)
    van_location_id = fields.Many2one(
        "stock.location",
        string="Van Stock Location",
        tracking=True,
        domain="[('usage', '=', 'internal')]",
        help="The internal inventory location assigned to this specific van."
    )

    van_salesman_id = fields.Many2one(
        "res.users",
        string="Salesman",
        tracking=True,
        domain="[('share', '=', False)]",
    )
    van_supervisor_id = fields.Many2one(
        "res.users",
        string="Supervisor",
        tracking=True,
        domain="[('share', '=', False)]",
    )
    van_pos_config_id = fields.Many2one(
        "pos.config",
        string="Van POS",
        readonly=True,
    )
    van_active = fields.Boolean(string="Van Active", default=True, tracking=True)
    van_notes = fields.Text(string="Van Notes")

    _sql_constraints = [
        (
            "van_code_unique",
            "unique(van_code)",
            "Van Code must be unique.",
        ),
    ]

    @api.constrains("is_van", "van_salesman_id")
    def _check_van_salesman(self):
        for vehicle in self:
            if vehicle.is_van and not vehicle.van_salesman_id:
                raise ValidationError(_("A Van Distribution Vehicle must have a Salesman."))

    def action_view_van_transfers(self):
        self.ensure_one()
        action = self.env.ref(
            "van_management_system.action_van_stock_transfer"
        ).read()[0]
        action["domain"] = [("van_id", "=", self.id)]
        action["context"] = {"default_van_id": self.id}
        return action

    def action_view_van_pos(self):
        self.ensure_one()
        if not self.van_pos_config_id:
            raise ValidationError(_("No POS configuration is linked to this van."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Van POS"),
            "res_model": "pos.config",
            "view_mode": "form",
            "res_id": self.van_pos_config_id.id,
        }


# ==========================================================
# POS ORDER INHERITANCE (Inabadilisha Source Location iwe ya Van)
# ==========================================================
class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _create_order_picking(self):
        res = super(PosOrder, self)._create_order_picking()
        
        for order in self:
            vehicle = self.env['fleet.vehicle'].search([
                ('is_van', '=', True),
                '|',
                ('van_salesman_id', '=', order.user_id.id),
                ('van_pos_config_id', '=', order.config_id.id)
            ], limit=1)

            if vehicle and vehicle.van_location_id:
                pickings = order.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel'))
                for picking in pickings:
                    picking.write({
                        'location_id': vehicle.van_location_id.id,
                    })
                    for move in picking.move_ids_without_package:
                        move.write({
                            'location_id': vehicle.van_location_id.id,
                        })
        return res


# ==========================================================
# STOCK PICKING INHERITANCE (Inashughulikia Returns & Transfers za Gari)
# ==========================================================
class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.model
    def create(self, vals):
        # Wakati picking inatengenezwa (kama vile Return), tunakagua kama inatoka au kuenda kwa gari la Salesman
        res = super(StockPicking, self).create(vals)
        
        # Angalia kama kuna user aliyeingia ambaye ni Salesman wa Van
        if res.user_id:
            vehicle = self.env['fleet.vehicle'].search([
                ('is_van', '=', True),
                ('van_salesman_id', '=', res.user_id.id)
            ], limit=1)
            
            # Kama ni Return (Destination ni WH/Stock au Internal Location kuu) na gari lina location
            script_dest = res.location_dest_id
            if vehicle and vehicle.van_location_id and script_dest and script_dest.usage == 'internal':
                # Kama inarudishwa stoku kuu kutoka kwenye gari
                if res.location_id == script_dest and script_dest != vehicle.van_location_id:
                    res.write({'location_id': vehicle.van_location_id.id})
                    for move in res.move_ids_without_package:
                        move.write({'location_id': vehicle.van_location_id.id})
                        
        return res