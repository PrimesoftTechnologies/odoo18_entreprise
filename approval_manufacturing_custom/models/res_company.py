from odoo import models, fields, api, exceptions, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    # ==========================================================
    # MANUFACTURING APPROVAL FLOW
    # ==========================================================

    use_approval_flow = fields.Boolean(
        string="Enable Manufacturing Approval Flow",
        compute='_compute_approval_flow',
        inverse='_inverse_approval_flow',
        help="Enable Manufacturing Approval Flow for this company."
    )

    manufacturing_approver_ids = fields.Many2many(
        'res.users',
        'res_company_manufacturing_approver_rel',
        'company_id',
        'user_id',
        string="Approvers",
        domain="[('company_ids', 'in', id)]",
        help="Users who are allowed to approve Manufacturing Orders."
    )

    # ==========================================================
    # MANUFACTURING INSPECTION FLOW
    # ==========================================================

    use_inspection_flow = fields.Boolean(
        string="Enable Manufacturing Inspection Flow",
        compute='_compute_inspection_flow',
        inverse='_inverse_inspection_flow',
        help="Enable Manufacturing Inspection Flow for this company."
    )

    manufacturing_inspector_ids = fields.Many2many(
        'res.users',
        'res_company_manufacturing_inspector_rel',
        'company_id',
        'user_id',
        string="Inspectors",
        domain="[('company_ids', 'in', id)]",
        help="Users who are allowed to complete Manufacturing Inspections."
    )

    # ==========================================================
    # COMPUTE APPROVAL FLOW
    # ==========================================================

    def _compute_approval_flow(self):

        Param = self.env['ir.config_parameter'].sudo()

        for company in self:

            value = Param.get_param(
                f'approval_manufacturing_custom.use_approval_flow_{company.id}',
                default='False'
            )

            company.use_approval_flow = (
                str(value).lower() in ('true', '1')
            )

    # ==========================================================
    # COMPUTE INSPECTION FLOW
    # ==========================================================

    def _compute_inspection_flow(self):

        Param = self.env['ir.config_parameter'].sudo()

        for company in self:

            value = Param.get_param(
                f'approval_manufacturing_custom.use_inspection_flow_{company.id}',
                default='False'
            )

            company.use_inspection_flow = (
                str(value).lower() in ('true', '1')
            )

    # ==========================================================
    # VALIDATION
    # ==========================================================

    @api.constrains(
        'use_approval_flow',
        'use_inspection_flow',
        'manufacturing_approver_ids',
        'manufacturing_inspector_ids',
    )
    def _check_manufacturing_workflow(self):

        for company in self:

            # ==================================================
            # RULE 1:
            # APPROVAL AND INSPECTION MUST MATCH
            # ==================================================

            if company.use_approval_flow != company.use_inspection_flow:

                raise exceptions.ValidationError(
                    _(
                        "MUST CHECK ALL\n\n"
                        "Manufacturing Approval Flow and Manufacturing "
                        "Inspection Flow must be enabled or disabled "
                        "together.\n\n"
                        "You cannot enable only one of them."
                    )
                )

            # ==================================================
            # RULE 2:
            # IF BOTH FLOWS ARE ENABLED
            # APPROVERS AND INSPECTORS ARE REQUIRED
            # ==================================================

            if (
                company.use_approval_flow
                and company.use_inspection_flow
            ):

                # ----------------------------------------------
                # APPROVERS REQUIRED
                # ----------------------------------------------

                if not company.manufacturing_approver_ids:

                    raise exceptions.ValidationError(
                        _(
                            "APPROVERS REQUIRED\n\n"
                            "Manufacturing Approval Flow is enabled, "
                            "but no Approver has been selected.\n\n"
                            "Please select at least one Approver "
                            "before saving."
                        )
                    )

                # ----------------------------------------------
                # INSPECTORS REQUIRED
                # ----------------------------------------------

                if not company.manufacturing_inspector_ids:

                    raise exceptions.ValidationError(
                        _(
                            "INSPECTORS REQUIRED\n\n"
                            "Manufacturing Inspection Flow is enabled, "
                            "but no Inspector has been selected.\n\n"
                            "Please select at least one Inspector "
                            "before saving."
                        )
                    )

    # ==========================================================
    # APPROVAL FLOW INVERSE
    # ==========================================================

    def _inverse_approval_flow(self):

        Param = self.env['ir.config_parameter'].sudo()

        for company in self:

            # --------------------------------------------------
            # BOTH FLOWS MUST MATCH
            # --------------------------------------------------

            if company.use_approval_flow != company.use_inspection_flow:

                raise exceptions.ValidationError(
                    _(
                        "MUST CHECK ALL\n\n"
                        "You cannot save the Manufacturing Flow "
                        "Settings with only one option enabled.\n\n"
                        "Enable BOTH options or disable BOTH options."
                    )
                )

            # --------------------------------------------------
            # IF ENABLED, USERS MUST EXIST
            # --------------------------------------------------

            if (
                company.use_approval_flow
                and company.use_inspection_flow
            ):

                if not company.manufacturing_approver_ids:

                    raise exceptions.ValidationError(
                        _(
                            "APPROVERS REQUIRED\n\n"
                            "Please select at least one Manufacturing "
                            "Approver before saving."
                        )
                    )

                if not company.manufacturing_inspector_ids:

                    raise exceptions.ValidationError(
                        _(
                            "INSPECTORS REQUIRED\n\n"
                            "Please select at least one Manufacturing "
                            "Inspector before saving."
                        )
                    )

            # --------------------------------------------------
            # SAVE APPROVAL PARAMETER
            # --------------------------------------------------

            Param.set_param(
                f'approval_manufacturing_custom.use_approval_flow_{company.id}',
                str(company.use_approval_flow)
            )

    # ==========================================================
    # INSPECTION FLOW INVERSE
    # ==========================================================

    def _inverse_inspection_flow(self):

        Param = self.env['ir.config_parameter'].sudo()

        for company in self:

            # --------------------------------------------------
            # BOTH FLOWS MUST MATCH
            # --------------------------------------------------

            if company.use_approval_flow != company.use_inspection_flow:

                raise exceptions.ValidationError(
                    _(
                        "MUST CHECK ALL\n\n"
                        "You cannot save the Manufacturing Flow "
                        "Settings with only one option enabled.\n\n"
                        "Enable BOTH options or disable BOTH options."
                    )
                )

            # --------------------------------------------------
            # IF ENABLED, USERS MUST EXIST
            # --------------------------------------------------

            if (
                company.use_approval_flow
                and company.use_inspection_flow
            ):

                if not company.manufacturing_approver_ids:

                    raise exceptions.ValidationError(
                        _(
                            "APPROVERS REQUIRED\n\n"
                            "Please select at least one Manufacturing "
                            "Approver before saving."
                        )
                    )

                if not company.manufacturing_inspector_ids:

                    raise exceptions.ValidationError(
                        _(
                            "INSPECTORS REQUIRED\n\n"
                            "Please select at least one Manufacturing "
                            "Inspector before saving."
                        )
                    )

            # --------------------------------------------------
            # SAVE INSPECTION PARAMETER
            # --------------------------------------------------

            Param.set_param(
                f'approval_manufacturing_custom.use_inspection_flow_{company.id}',
                str(company.use_inspection_flow)
            )