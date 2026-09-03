from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    sas_reference = fields.Char(string="SAS Reference")
    antrak_job_no = fields.Char(string="Antrak Job No")


# 1. Hifadhi ya Kudumu (Database Record) kwa ajili ya Batch zote zinazozalishwa
class BatchInvoice(models.Model):
    _name = 'batch.invoice'
    _description = 'Batch Invoice Record'
    _order = 'id desc'

    name = fields.Char(string="Batch ID / Number", readonly=True, default="New")
    line_ids = fields.One2many(
        'batch.invoice.line',
        'batch_id',
        string="Batch Lines"
    )

    def action_print_batch(self):
        # Kitufe cha kurejesha Print / PDF baadaye ukifungua kihistoria
        return self.env.ref(
            'batch_generate_invoice.action_report_batch_invoice'
        ).report_action(self)


class BatchInvoiceLine(models.Model):
    _name = 'batch.invoice.line'
    _description = 'Batch Invoice Line'

    batch_id = fields.Many2one(
        'batch.invoice',
        string="Batch Reference",
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
    sas_reference = fields.Char(string="SAS Reference")
    antrak_job_no = fields.Char(string="Antrak Job No")
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


# 2. Wizard ya kuchagua na kuhariri kabla ya kutengeneza
class BatchInvoiceWizard(models.TransientModel):
    _name = 'batch.invoice.wizard'
    _description = 'Generate Batch Invoice Wizard'

    name = fields.Char(string="Batch Number", readonly=True, default="New")
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
        # A. Tengeneza namba/ID rasmi ya Batch kutumia sequence
        batch_name = self.env['ir.sequence'].next_by_code('batch.invoice.sequence') or 'BATCH/2026/001'

        # B. Hifadhi taarifa kwenye Model ya Kudumu (BatchInvoice) ili ionekane kwenye orodha ya Batch
        batch_vals = {
            'name': batch_name,
            'line_ids': []
        }

        for line in self.line_ids:
            # Sasisha data kwenye ukurasa wa ankara (Invoice) kama ilivyohaririwa
            if line.invoice_id:
                line.invoice_id.write({
                    'sas_reference': line.sas_reference,
                    'antrak_job_no': line.antrak_job_no,
                })
            
            # Weka mistari kwenye hifadhi ya kudumu ya batch
            batch_vals['line_ids'].append((0, 0, {
                'invoice_id': line.invoice_id.id,
                'sas_reference': line.sas_reference,
                'antrak_job_no': line.antrak_job_no,
            }))

        new_batch = self.env['batch.invoice'].create(batch_vals)

        # C. Kutoa print (PDF) moja kwa moja na kufungua orodha ya batch chini ya menyu ya Customers
        return self.env.ref(
            'batch_generate_invoice.action_report_batch_invoice'
        ).report_action(new_batch)


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
    sas_reference = fields.Char(string="SAS Reference")
    antrak_job_no = fields.Char(string="Antrak Job No")
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