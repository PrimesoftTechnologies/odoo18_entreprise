# -*- coding: utf-8 -*-
import io
import base64
from odoo import models, fields, api, _
from odoo.exceptions import UserError

try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None


class ClearanceReportWizard(models.TransientModel):
    """Filter wizard that drives both the PDF (QWeb) and Excel exports of
    the Clearance Report, matching the layout of the legacy sample report.
    """
    _name = 'sas.clearance.report.wizard'
    _description = 'Clearance Report Filters'

    date_from = fields.Date(string='ETA From')
    date_to = fields.Date(string='ETA To')
    order_type = fields.Selection(
        [('import', 'Import'), ('export', 'Export'), ('transit', 'Transit'),
         ('domestic', 'Domestic'), ('local delivery', 'Local Delivery'), ('other', 'Others')],
        string='Order Type',
    )
    transport_mode = fields.Selection(
        [('sea', 'Sea'), ('air', 'Air'), ('land', 'Road')], string='Transport Mode',
    )
    state = fields.Selection(
        [('draft', 'Draft'), ('submitted', 'Submitted'), ('confirmed', 'Confirmed'),
         ('arrived', 'Arrived'), ('clearing', 'Clearing'), ('cleared', 'Cleared'),
         ('received', 'Stock Received'), ('transported', 'Transported'),
         ('delivered', 'Delivered'), ('done', 'Done'), ('cancelled', 'Cancelled')],
        string='Status',
    )
    consignee_id = fields.Many2one('res.partner', string='Consignee')
    responsible_user_id = fields.Many2one('res.users', string='Clearing Officer')
    only_overdue = fields.Boolean(string='Overdue Only')

    # ------------------------------------------------------------------
    # DOMAIN
    # ------------------------------------------------------------------
    def _get_domain(self):
        self.ensure_one()
        domain = []
        if self.date_from:
            domain.append(('eta', '>=', self.date_from))
        if self.date_to:
            domain.append(('eta', '<=', self.date_to))
        if self.order_type:
            domain.append(('order_type', '=', self.order_type))
        if self.transport_mode:
            domain.append(('transport_mode', '=', self.transport_mode))
        if self.state:
            domain.append(('state', '=', self.state))
        if self.consignee_id:
            domain.append(('consignee_id', '=', self.consignee_id.id))
        if self.only_overdue:
            domain.append(('is_overdue', '=', True))
        if self.responsible_user_id:
            domain.append(('clearance_ids.responsible_user_id', '=', self.responsible_user_id.id))
        return domain

    def _get_orders(self):
        return self.env['shipping.order'].search(self._get_domain(), order='eta asc, name asc')

    # ------------------------------------------------------------------
    # PDF
    # ------------------------------------------------------------------
    def action_print_pdf(self):
        self.ensure_one()
        orders = self._get_orders()
        if not orders:
            raise UserError(_("No shipping orders match the selected filters."))
        return self.env.ref('sas.action_report_clearance_report').report_action(orders, data={
            'wizard_id': self.id,
        })

    # ------------------------------------------------------------------
    # EXCEL
    # ------------------------------------------------------------------
    def action_export_xlsx(self):
        self.ensure_one()
        if xlsxwriter is None:
            raise UserError(_("The 'xlsxwriter' Python library is not installed on the server."))

        orders = self._get_orders()
        if not orders:
            raise UserError(_("No shipping orders match the selected filters."))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Clearance Report')

        header_fmt = workbook.add_format({
            'bold': True, 'bg_color': '#305496', 'font_color': 'white',
            'border': 1, 'align': 'center', 'valign': 'vcenter', 'text_wrap': True,
        })
        cell_fmt = workbook.add_format({'border': 1, 'valign': 'vcenter'})
        date_fmt = workbook.add_format({'border': 1, 'valign': 'vcenter', 'num_format': 'dd-mmm-yy'})
        money_fmt = workbook.add_format({'border': 1, 'valign': 'vcenter', 'num_format': '#,##0.00'})

        headers = [
            'File No', 'IntRefNo', 'Consignee', 'B/L No', 'B/L Date', 'Cargo Desc',
            'Supplier Invoice', 'Client PO', 'Packages/Container Details', 'Quantity',
            'Size', 'Weight', 'Pad No', 'Pad Reg-No', 'Assessed date', 'Duty amount',
            'Duty Paid Date', 'Vessel /Flight name', 'Port of Loading', 'ETA', 'ATA',
            'RFD date', 'REMARKS',
        ]
        col_widths = [10, 12, 24, 16, 11, 24, 16, 14, 26, 9, 8, 11, 10, 16, 12, 12, 12, 18, 18, 11, 11, 11, 20]
        for col, (title, width) in enumerate(zip(headers, col_widths)):
            sheet.write(0, col, title, header_fmt)
            sheet.set_column(col, col, width)
        sheet.freeze_panes(1, 0)

        row = 1
        for order in orders:
            containers = ', '.join(filter(None, order.line_ids.mapped('container_number')))
            sizes = ', '.join(sorted(set(filter(None, order.line_ids.mapped('container_type'))))) or (
                order.sea_shipment_type or order.land_shipment_type or order.air_shipment_type or ''
            )
            cargo_desc = ', '.join(filter(None, order.line_ids.mapped('cargo_description')))
            remarks = order.remarks or ''

            values = [
                order.name or '', order.name or '', order.consignee_id.name or '',
                order.bl_awb_number or '', order.bl_awb_date, cargo_desc,
                order.supplier_invoice_no or '', order.client_po_number or '',
                containers or order.pad_number or '', order.total_quantity, sizes,
                order.total_weight, order.pad_number or '', order.pad_reg_number or '',
                order.assessed_date, order.duty_amount, order.duty_paid_date,
                order.vessel_flight_name or '', order.loading_port_id.name or '',
                order.eta, order.ata, order.rfd_date, remarks,
            ]
            date_cols = {4, 14, 16, 19, 20, 21}
            money_cols = {15}
            for col, val in enumerate(values):
                if val is False or val is None:
                    val = ''
                if col in date_cols and val:
                    sheet.write_datetime(row, col, val, date_fmt)
                elif col in money_cols:
                    sheet.write_number(row, col, val or 0.0, money_fmt)
                else:
                    sheet.write(row, col, val, cell_fmt)
            row += 1

        workbook.close()
        output.seek(0)

        attachment = self.env['ir.attachment'].create({
            'name': 'Clearance_Report.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(output.read()),
            'res_model': 'sas.clearance.report.wizard',
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'self',
        }
