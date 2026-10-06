import io
import base64
from odoo import models, fields, _
from odoo.exceptions import UserError

try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None


class SasClearanceReportWizard(models.TransientModel):
    _inherit = 'sas.clearance.report.wizard'

    # Ikiachwa wazi, ripoti inajumuisha shippers wote (ALL)
    sas_shipper = fields.Many2one(
        'res.partner', string='Shipper',
        help="Leave empty to include all shippers.",
    )

    def _get_domain(self):
        # Ongeza kichujio cha shipper juu ya vichujio vya asili vya sas
        domain = super()._get_domain()
        if self.sas_shipper:
            domain.append(('shipper_id', '=', self.sas_shipper.id))
        return domain

    def action_export_xlsx(self):
        # Inachukua nafasi ya export ya asili ili kuongeza column ya Shipper
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
            'File No', 'IntRefNo', 'Shipper', 'Consignee', 'B/L No', 'B/L Date', 'Cargo Desc',
            'Supplier Invoice', 'Client PO', 'Packages/Container Details', 'Quantity',
            'Size', 'Weight', 'Pad No', 'Pad Reg-No', 'Assessed date', 'Duty amount',
            'Duty Paid Date', 'Vessel /Flight name', 'Port of Loading', 'ETA', 'ATA',
            'RFD date', 'REMARKS',
        ]
        col_widths = [10, 12, 24, 24, 16, 11, 24, 16, 14, 26, 9, 8, 11, 10, 16, 12, 12, 12, 18, 18, 11, 11, 11, 20]
        for col, (title, width) in enumerate(zip(headers, col_widths)):
            sheet.write(0, col, title, header_fmt)
            sheet.set_column(col, col, width)
        sheet.freeze_panes(1, 0)

        date_cols = {5, 15, 17, 20, 21, 22}
        money_cols = {16}
        row = 1
        for order in orders:
            containers = ', '.join(filter(None, order.line_ids.mapped('container_number')))
            sizes = ', '.join(sorted(set(filter(None, order.line_ids.mapped('container_type'))))) or (
                order.sea_shipment_type or order.land_shipment_type or order.air_shipment_type or ''
            )
            cargo_desc = ', '.join(filter(None, order.line_ids.mapped('cargo_description')))
            remarks = order.remarks or ''

            values = [
                order.name or '', order.name or '', order.shipper_id.name or '',
                order.consignee_id.name or '',
                order.bl_awb_number or '', order.bl_awb_date, cargo_desc,
                order.supplier_invoice_no or '', order.client_po_number or '',
                containers or order.pad_number or '', order.total_quantity, sizes,
                order.total_weight, order.pad_number or '', order.pad_reg_number or '',
                order.assessed_date, order.duty_amount, order.duty_paid_date,
                order.vessel_flight_name or '', order.loading_port_id.name or '',
                order.eta, order.ata, order.rfd_date, remarks,
            ]
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
