from odoo import models, fields, api, exceptions, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # ==========================================================
    # APPROVAL FLOW
    # ==========================================================

    use_approval_flow = fields.Boolean(
        string="Enable Manufacturing Approval Flow",
        related='company_id.use_approval_flow',
        readonly=False,
    )

    # ==========================================================
    # INSPECTION FLOW
    # ==========================================================

    use_inspection_flow = fields.Boolean(
        string="Enable Manufacturing Inspection Flow",
        related='company_id.use_inspection_flow',
        readonly=False,
    )

    # ==========================================================
    # VALIDATION
    # ==========================================================

    @api.constrains(
        'use_approval_flow',
        'use_inspection_flow'
    )
    def _check_flow_settings(self):

        for record in self:

            if record.use_approval_flow != record.use_inspection_flow:

                raise exceptions.ValidationError(
                    _(
                        "MUST CHECK ALL:\n\n"
                        "You cannot save the Manufacturing Flow Settings "
                        "with only one option enabled.\n\n"
                        "Enable BOTH options or disable BOTH options."
                    )
                )