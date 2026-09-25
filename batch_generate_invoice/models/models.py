from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    sas_reference = fields.Char(string="SAS Reference")
    antrak_job_no = fields.Char(string="Antrak Job No")
    po_no = fields.Char(string="PO No")
    terms_template_id = fields.Many2one('sale.terms.template', string="Bank Details For Payment", ondelete='set null')


class BatchInvoice(models.Model):
    _name = 'batch.invoice'
    _description = 'Batch Invoice Record'
    _order = 'id desc'

    name = fields.Char(string="Batch ID / Number", readonly=True, default="New")
    bank_details_id = fields.Many2one('sale.terms.template', string="Bank Details For Payment", readonly=True, ondelete='set null')
    due_date = fields.Date(string="Due Date", readonly=True)
    separable_portion = fields.Selection([
        ('01', 'SP-01'),
        ('02', 'SP-02')
    ], string='Separable Portion', readonly=True, default='01')
    
    add_vat = fields.Boolean(string="Add 18% VAT", readonly=True)
    subtotal_amount = fields.Monetary(string="Subtotal", compute='_compute_amounts', currency_field='currency_id')
    vat_amount = fields.Monetary(string="18% VAT", compute='_compute_amounts', currency_field='currency_id')
    total_amount = fields.Monetary(string="Final Total", compute='_compute_amounts', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', compute='_compute_amounts')

    @api.depends('line_ids.amount', 'add_vat')
    def _compute_amounts(self):
        for record in self:
            # Hapa inachukua jumla ya kiasi cha invoice zote zilizomo (mfano 2,000,000)
            subtotal = sum(record.line_ids.mapped('amount'))
            record.subtotal_amount = subtotal
            
            if record.add_vat:
                # Inapiga 18% ya subtotal (mfano 2,000,000 * 0.18 = 360,000)
                vat = subtotal * 0.18
                record.vat_amount = vat
                # Inajumlisha subtotal + vat (2,000,000 + 360,000 = 2,360,000)
                record.total_amount = subtotal + vat
            else:
                record.vat_amount = 0.0
                record.total_amount = subtotal
                
            first_inv = record.line_ids[:1].invoice_id
            record.currency_id = first_inv.currency_id.id if first_inv else self.env.company.currency_id.id

    line_ids = fields.One2many(
        'batch.invoice.line',
        'batch_id',
        string="Batch Lines"
    )

    def action_print_batch(self):
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
    po_no = fields.Char(string="PO No")
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


class BatchInvoiceWizard(models.TransientModel):
    _name = 'batch.invoice.wizard'
    _description = 'Generate Batch Invoice Wizard'

    name = fields.Char(string="Batch Number", readonly=True, default="New")
    bank_details_id = fields.Many2one('sale.terms.template', string="Bank Details For Payment", ondelete='set null')
    due_date = fields.Date(string="Due Date")
    separable_portion = fields.Selection([
        ('01', 'SP-01'),
        ('02', 'SP-02')
    ], string='Separable Portion', default='01', required=True)
    
    add_vat = fields.Boolean(string="Add 18% VAT")
    
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
                'po_no': inv.po_no or '',
            }))

        res['line_ids'] = lines
        return res

    def action_generate_batch(self):
        batch_name = self.env['ir.sequence'].next_by_code('batch.invoice.sequence') or 'BATCH/2026/001'

        batch_vals = {
            'name': batch_name,
            'bank_details_id': self.bank_details_id.id if self.bank_details_id else False,
            'due_date': self.due_date,
            'separable_portion': self.separable_portion,
            'add_vat': self.add_vat, # Hii inahifadhi kama VAT ilichaguliwa au la kwenye batch halisi
            'line_ids': []
        }

        for line in self.line_ids:
            if line.invoice_id:
                write_vals = {
                    'sas_reference': line.sas_reference,
                    'antrak_job_no': line.antrak_job_no,
                    'po_no': line.po_no,
                }
                if self.bank_details_id:
                    write_vals['terms_template_id'] = self.bank_details_id.id
                line.invoice_id.write(write_vals)
            
            batch_vals['line_ids'].append((0, 0, {
                'invoice_id': line.invoice_id.id,
                'sas_reference': line.sas_reference,
                'antrak_job_no': line.antrak_job_no,
                'po_no': line.po_no,
            }))

        new_batch = self.env['batch.invoice'].create(batch_vals)

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
    po_no = fields.Char(string="PO No")
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