from odoo import models, fields

class FleetVehicle(models.Model):
    _inherit = "fleet.vehicle"


    def _compute_display_name(self):
        for vehicle in self:
            vehicle.display_name = vehicle.license_plate or ''

    # ==================== NEW TRA Owner / Title Holder Fields ====================
    tra_tin = fields.Char(string="TIN", help="Tax Identification Number from TRA card")
    owner_category = fields.Selection(
        selection=[("individual", "Individual"), ("limited_company", "Limited Company"),
                   ("partnership", "Partnership"), ("other", "Other")],
        string="Owner Category",
    )
    title_holder_tin = fields.Char(string="Title Holder TIN")
    title_holder_category = fields.Selection(
        selection=[("individual", "Individual"), ("limited_company", "Limited Company"),
                   ("partnership", "Partnership"), ("other", "Other")],
        string="Title Holder Category",
    )
    title_holder_name = fields.Char(string="Title Holder Name")

    # ==================== NEW TRA Vehicle Details ====================
    body_type = fields.Char(string="Body Type")
    vehicle_color = fields.Char(string="Color")
    vehicle_class = fields.Char(string="Class")
    year_of_manufacture = fields.Integer(string="Year of Manufacture")
    engine_no = fields.Char(string="Engine No")
    engine_capacity = fields.Float(string="Engine Capacity (cc)")
    number_of_axles = fields.Integer(string="Number of Axles")
    seating_capacity = fields.Integer(string="Seating Capacity")
    gross_weight = fields.Float(string="Gross Weight (kg)")
    tare_weight = fields.Float(string="Tare Weight (kg)")
    imported_from = fields.Char(string="Imported From")

    # ==================== NEW TRA Card & Tax Fields ====================
    date_first_registration = fields.Date(string="Date of First Registration")
    tra_vrc_sn = fields.Char(string="TRA VRC SN", help="Vehicle Registration Card Serial Number")
    previous_registration = fields.Char(string="Previous Registration")
    tax_roll_status = fields.Selection(
        selection=[("import_duty_not_exempted", "Import Duty Not Exempted"),
                   ("exempted", "Exempted"), ("other", "Other")],
        string="Tax Roll Status",
    )
    vehicle_usage = fields.Selection(
        selection=[("private_normal", "Private / Normal"),
                   ("commercial", "Commercial"),
                   ("public_service", "Public Service")],
        string="Vehicle Usage",
    )

    tra_registration_card = fields.Binary(string="TRA Registration Card", attachment=True)
    tra_registration_card_filename = fields.Char()


class FleetVehicleLogContract(models.Model):
    _inherit = 'fleet.vehicle.log.contract'

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        readonly=False,
        default=lambda self: self.env.company.currency_id,
    )