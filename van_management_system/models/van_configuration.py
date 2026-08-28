from odoo import api, fields, models, _


# ==============================================================
# VAN CONFIGURATION
# ==============================================================

class VanConfiguration(models.Model):
    _name = "van.configuration"
    _description = "Van Distribution Configuration"
    _rec_name = "name"

    # ==========================================================
    # BASIC INFORMATION
    # ==========================================================

    name = fields.Char(
        string="Configuration Name",
        required=True,
        default="Van Distribution Settings",
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    active = fields.Boolean(
        string="Active",
        default=True,
    )

    # ==========================================================
    # VAN SETTINGS
    # ==========================================================

    default_van_active = fields.Boolean(
        string="Vans Active by Default",
        default=True,
        help="New Van Distribution vehicles will be active by default.",
    )

    allow_salesman_van_selection = fields.Boolean(
        string="Allow Salesman Van Selection",
        default=True,
        help="Allow Salesmen to select their assigned Van.",
    )

    # ==========================================================
    # ROUTE CONFIGURATION
    # ==========================================================

    route_required_transfer = fields.Boolean(
        string="Require Internal Transfer",
        default=True,
        help="A Sales Route must have an Internal Transfer before it can be planned.",
    )

    route_require_locations = fields.Boolean(
        string="Require Start and End Locations",
        default=True,
        help="Require Start Location and End Location on Sales Routes.",
    )

    # ==========================================================
    # STOCK TRANSFER SETTINGS
    # ==========================================================

    require_transfer_approval = fields.Boolean(
        string="Require Stock Transfer Approval",
        default=True,
        help="Stock Loading and Stock Return requests must be approved before validation.",
    )

    allow_partial_approval = fields.Boolean(
        string="Allow Partial Approval",
        default=True,
        help="Allow the approver to approve less than the requested quantity.",
    )

    require_stock_check = fields.Boolean(
        string="Check Available Stock",
        default=True,
        help="Check available stock before approving Stock Loading.",
    )

    # ==========================================================
    # APPROVAL SETTINGS
    # ==========================================================

    require_supervisor_approval = fields.Boolean(
        string="Supervisor Approval",
        default=True,
        help="Require Supervisor approval for Van Stock Transfers.",
    )

    require_manager_approval = fields.Boolean(
        string="Manager Approval",
        default=False,
        help="Require Manager approval for Van Stock Transfers.",
    )

    approval_user_ids = fields.Many2many(
        "res.users",
        "van_configuration_approval_user_rel",
        "configuration_id",
        "user_id",
        string="Approval Users",
        help="Users allowed to approve Van Stock Transfers.",
    )

    # ==========================================================
    # NOTES
    # ==========================================================

    note = fields.Text(
        string="Notes",
    )

    # ==========================================================
    # CONSTRAINT
    # ==========================================================

    @api.constrains("company_id")
    def _check_company(self):
        for record in self:
            if not record.company_id:
                record.company_id = self.env.company

    # ==========================================================
    # DEFAULT CONFIGURATION
    # ==========================================================

    @api.model
    def get_configuration(self, company=None):
        """
        Return the active Van Distribution configuration
        for the selected company.
        """

        company = company or self.env.company

        configuration = self.search(
            [
                ("company_id", "=", company.id),
                ("active", "=", True),
            ],
            limit=1,
        )

        if not configuration:
            configuration = self.create(
                {
                    "name": _("Van Distribution Settings"),
                    "company_id": company.id,
                }
            )

        return configuration

    # ==========================================================
    # OPEN CONFIGURATION
    # ==========================================================

    def action_open_configuration(self):
        self.ensure_one()

        return {
            "type": "ir.actions.act_window",
            "name": _("Van Settings"),
            "res_model": "van.configuration",
            "view_mode": "form",
            "res_id": self.id,
            "target": "current",
        }


# ==============================================================
# ROUTE CONFIGURATION
# ==============================================================

class VanRouteConfiguration(models.Model):
    _name = "van.route.configuration"
    _description = "Van Route Configuration"
    _rec_name = "name"

    name = fields.Char(
        string="Configuration Name",
        required=True,
        default="Route Configuration",
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    active = fields.Boolean(
        string="Active",
        default=True,
    )

    require_route_date = fields.Boolean(
        string="Require Route Date",
        default=True,
    )

    require_start_location = fields.Boolean(
        string="Require Start Location",
        default=True,
    )

    require_end_location = fields.Boolean(
        string="Require End Location",
        default=True,
    )

    require_van = fields.Boolean(
        string="Require Van",
        default=True,
    )

    require_internal_transfer = fields.Boolean(
        string="Require Internal Transfer",
        default=True,
    )

    allow_route_cancellation = fields.Boolean(
        string="Allow Route Cancellation",
        default=True,
    )

    note = fields.Text(
        string="Notes",
    )

    @api.model
    def get_configuration(self, company=None):
        company = company or self.env.company

        configuration = self.search(
            [
                ("company_id", "=", company.id),
                ("active", "=", True),
            ],
            limit=1,
        )

        if not configuration:
            configuration = self.create(
                {
                    "name": _("Route Configuration"),
                    "company_id": company.id,
                }
            )

        return configuration


# ==============================================================
# STOCK TRANSFER CONFIGURATION
# ==============================================================

class VanStockTransferConfiguration(models.Model):
    _name = "van.stock.transfer.configuration"
    _description = "Van Stock Transfer Configuration"
    _rec_name = "name"

    name = fields.Char(
        string="Configuration Name",
        required=True,
        default="Stock Transfer Settings",
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    active = fields.Boolean(
        string="Active",
        default=True,
    )

    require_approval = fields.Boolean(
        string="Require Approval",
        default=True,
    )

    check_available_stock = fields.Boolean(
        string="Check Available Stock",
        default=True,
    )

    allow_partial_approval = fields.Boolean(
        string="Allow Partial Approval",
        default=True,
    )

    auto_create_inventory_transfer = fields.Boolean(
        string="Create Inventory Transfer Automatically",
        default=True,
        help="Automatically create the Odoo Inventory Transfer after approval.",
    )

    note = fields.Text(
        string="Notes",
    )

    @api.model
    def get_configuration(self, company=None):
        company = company or self.env.company

        configuration = self.search(
            [
                ("company_id", "=", company.id),
                ("active", "=", True),
            ],
            limit=1,
        )

        if not configuration:
            configuration = self.create(
                {
                    "name": _("Stock Transfer Settings"),
                    "company_id": company.id,
                }
            )

        return configuration


# ==============================================================
# APPROVAL CONFIGURATION
# ==============================================================

class VanApprovalConfiguration(models.Model):
    _name = "van.approval.configuration"
    _description = "Van Approval Configuration"
    _rec_name = "name"

    name = fields.Char(
        string="Configuration Name",
        required=True,
        default="Approval Settings",
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    active = fields.Boolean(
        string="Active",
        default=True,
    )

    require_supervisor = fields.Boolean(
        string="Supervisor Approval",
        default=True,
    )

    require_manager = fields.Boolean(
        string="Manager Approval",
        default=False,
    )

    approval_user_ids = fields.Many2many(
        "res.users",
        "van_approval_configuration_user_rel",
        "configuration_id",
        "user_id",
        string="Approval Users",
    )

    allow_rejection = fields.Boolean(
        string="Allow Rejection",
        default=True,
    )

    require_rejection_reason = fields.Boolean(
        string="Require Rejection Reason",
        default=True,
    )

    note = fields.Text(
        string="Notes",
    )

    @api.model
    def get_configuration(self, company=None):
        company = company or self.env.company

        configuration = self.search(
            [
                ("company_id", "=", company.id),
                ("active", "=", True),
            ],
            limit=1,
        )

        if not configuration:
            configuration = self.create(
                {
                    "name": _("Approval Settings"),
                    "company_id": company.id,
                }
            )

        return configuration

