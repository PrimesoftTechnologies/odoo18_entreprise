from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    sas_reference = fields.Char(string="SAS Reference")
    antrak_job_no = fields.Char(string="Antrak Job No")


class BatchInvoiceWizard(models.TransientModel):
    _name = 'batch.invoice.wizard'
    _description = 'Generate Batch Invoice Wizard'

    line_ids = fields.One2many(
        'batch.invoice.wizard.line',
        'wizard_id',
        string="Invoice Lines"
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_ids = self.env.context.get('active_ids', [])
        invoices = self.env['account.move'].browse(active_ids).exists()

        lines = []
        for inv in invoices:
            lines.append((0, 0, {
                'invoice_id': inv.id,
                'sas_reference': inv.sas_reference or '',
                'antrak_job_no': inv.antrak_job_no or '',
            }))

        res['line_ids'] = lines
        return res

    def action_generate_batch(self):
        for line in self.line_ids:
            if line.invoice_id:
                line.invoice_id.write({
                    'sas_reference': line.sas_reference,
                    'antrak_job_no': line.antrak_job_no,
                })

        return self.env.ref(
            'batch_generate_invoice.action_report_batch_invoice'
        ).report_action(self)


class BatchInvoiceWizardLine(models.TransientModel):
    _name = 'batch.invoice.wizard.line'
    _description = 'Batch Invoice Wizard Line'

    wizard_id = fields.Many2one(
        'batch.invoice.wizard',
        string="Wizard",
        required=True,
        ondelete='cascade'
    )

    invoice_id = fields.Many2one(
        'account.move',
        string="Invoice",
        required=True
    )

    invoice_date = fields.Date(
        related='invoice_id.invoice_date',
        string="Invoice Date",
        readonly=True
    )

    invoice_number = fields.Char(
        related='invoice_id.name',
        string="Invoice Number",
        readonly=True
    )

    sas_reference = fields.Char(
        string="SAS Reference"
    )

    antrak_job_no = fields.Char(
        string="Antrak Job No"
    )

    # Tumia Related Fields kwa Currency na Amount ili zisome moja kwa moja kutoka kwenye Invoice
    currency_id = fields.Many2one(
        related='invoice_id.currency_id',
        string="Currency",
        readonly=True
    )

    amount = fields.Monetary(
        related='invoice_id.amount_total',
        string="Amount",
        currency_field='currency_id',
        readonly=True
    )