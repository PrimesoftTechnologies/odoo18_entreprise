from odoo import models, fields, api
from odoo.exceptions import ValidationError

import io
import base64
import xlsxwriter
from datetime import timedelta


class CommissionReportWizard(models.TransientModel):

    _name = "commission.report.wizard"
    _description = "Employee Commission Report Wizard"

    # ==========================================================
    # EMPLOYEE SELECTION
    # ==========================================================

    employee_selection = fields.Selection(
        selection=[
            ("all", "All Employees"),
            ("employee", "Specific Employee"),
        ],
        string="Employee",
        default="all",
        required=True,
    )

    employee_id = fields.Many2one(
        "hr.employee",
        string="Employee",
    )

    # ==========================================================
    # POINT OF SALE
    # ==========================================================

    pos_config_id = fields.Many2one(
        "pos.config",
        string="Point of Sale",
        help="Select the Point of Sale to include in the report.",
    )

    # ==========================================================
    # DATE RANGE
    # ==========================================================

    date_from = fields.Date(
        string="From Date",
        required=True,
    )

    date_to = fields.Date(
        string="To Date",
        required=True,
    )

    # ==========================================================
    # ONCHANGE
    # ==========================================================

    @api.onchange("employee_selection")
    def _onchange_employee_selection(self):

        if self.employee_selection == "all":
            self.employee_id = False

    # ==========================================================
    # VALIDATION
    # ==========================================================

    @api.constrains("date_from", "date_to")
    def _check_dates(self):

        for record in self:

            if (
                record.date_from
                and record.date_to
                and record.date_from > record.date_to
            ):
                raise ValidationError(
                    "From Date cannot be later than To Date."
                )

    @api.constrains("employee_selection", "employee_id")
    def _check_employee_selection(self):

        for record in self:

            if (
                record.employee_selection == "employee"
                and not record.employee_id
            ):
                raise ValidationError(
                    "Please select an employee."
                )

    # ==========================================================
    # GET REPORT DOMAIN
    # ==========================================================

    def _get_report_domain(self):

        self.ensure_one()

        domain = []

        # ------------------------------------------------------
        # EMPLOYEE FILTER
        # ------------------------------------------------------

        if (
            self.employee_selection == "employee"
            and self.employee_id
        ):

            domain.append(
                (
                    "employee_id",
                    "=",
                    self.employee_id.id,
                )
            )

        # ------------------------------------------------------
        # POINT OF SALE FILTER
        # ------------------------------------------------------
        #
        # IMPORTANT:
        #
        # pos.order.line
        #       ↓
        # order_id
        #       ↓
        # config_id
        #
        # When a POS is selected, ONLY orders belonging
        # to that POS configuration will be included.
        #
        # When POS is empty, ALL POS configurations are included.
        #
        # ------------------------------------------------------

        if self.pos_config_id:

            domain.append(
                (
                    "order_id.config_id",
                    "=",
                    self.pos_config_id.id,
                )
            )

        # ------------------------------------------------------
        # FROM DATE
        # ------------------------------------------------------

        if self.date_from:

            date_from_datetime = fields.Datetime.to_datetime(
                self.date_from
            )

            domain.append(
                (
                    "order_id.date_order",
                    ">=",
                    date_from_datetime,
                )
            )

        # ------------------------------------------------------
        # TO DATE
        # ------------------------------------------------------

        if self.date_to:

            date_to_datetime = (
                fields.Datetime.to_datetime(
                    self.date_to
                )
                + timedelta(days=1)
            )

            domain.append(
                (
                    "order_id.date_order",
                    "<",
                    date_to_datetime,
                )
            )

        # ------------------------------------------------------
        # ONLY EMPLOYEE COMMISSION LINES
        # ------------------------------------------------------

        domain.append(
            (
                "employee_id",
                "!=",
                False,
            )
        )

        # ------------------------------------------------------
        # ONLY POSITIVE COMMISSION
        # ------------------------------------------------------

        domain.append(
            (
                "commission_amount",
                ">",
                0,
            )
        )

        return domain

    # ==========================================================
    # GET EMPLOYEE DATA
    # ==========================================================

    def _get_employee_data(self):

        self.ensure_one()

        domain = self._get_report_domain()

        # ------------------------------------------------------
        # GET POS ORDER LINES
        # ------------------------------------------------------

        lines = self.env[
            "pos.order.line"
        ].search(
            domain,
            order="employee_id, order_id, id",
        )

        # ------------------------------------------------------
        # GROUP BY EMPLOYEE
        # ------------------------------------------------------

        employees = {}

        for line in lines:

            employee = line.employee_id

            if not employee:
                continue

            if employee.id not in employees:

                employees[employee.id] = {

                    "name": employee.name,

                    "lines": [],

                    "total_price": 0.0,

                    "total_commission": 0.0,

                }

            # --------------------------------------------------
            # ADD LINE
            # --------------------------------------------------

            employees[
                employee.id
            ][
                "lines"
            ].append(line)

            # --------------------------------------------------
            # TOTAL PRICE
            # --------------------------------------------------

            line_total_price = (
                (line.qty or 0.0)
                *
                (line.price_unit or 0.0)
            )

            employees[
                employee.id
            ][
                "total_price"
            ] += line_total_price

            # --------------------------------------------------
            # TOTAL COMMISSION
            # --------------------------------------------------

            employees[
                employee.id
            ][
                "total_commission"
            ] += (
                line.commission_amount or 0.0
            )

        # ------------------------------------------------------
        # GRAND TOTALS
        # ------------------------------------------------------

        grand_total_price = sum(
            employee["total_price"]
            for employee in employees.values()
        )

        grand_total_commission = sum(
            employee["total_commission"]
            for employee in employees.values()
        )

        return (
            employees,
            grand_total_price,
            grand_total_commission,
        )

    # ==========================================================
    # PRINT PDF
    # ==========================================================

    def action_print_report(self):

        self.ensure_one()

        # ------------------------------------------------------
        # VALIDATE EMPLOYEE
        # ------------------------------------------------------

        if (
            self.employee_selection == "employee"
            and not self.employee_id
        ):

            raise ValidationError(
                "Please select an employee."
            )

        # ------------------------------------------------------
        # VALIDATE DATES
        # ------------------------------------------------------

        if (
            self.date_from
            and self.date_to
            and self.date_from > self.date_to
        ):

            raise ValidationError(
                "From Date cannot be later than To Date."
            )

        # ------------------------------------------------------
        # REPORT DATA
        # ------------------------------------------------------

        data = {

            "employee_selection":
                self.employee_selection,

            "employee_id": (
                self.employee_id.id
                if (
                    self.employee_selection == "employee"
                    and self.employee_id
                )
                else False
            ),

            "pos_config_id": (
                self.pos_config_id.id
                if self.pos_config_id
                else False
            ),

            "date_from":
                self.date_from,

            "date_to":
                self.date_to,

        }

        # ------------------------------------------------------
        # PRINT REPORT
        # ------------------------------------------------------

        return self.env.ref(
            "salon_pos_custom.action_employee_commission_report"
        ).report_action(
            self,
            data=data,
        )

    # ==========================================================
    # EXPORT EXCEL
    # ==========================================================

    def action_export_excel(self):

        self.ensure_one()

        # ------------------------------------------------------
        # VALIDATE EMPLOYEE
        # ------------------------------------------------------

        if (
            self.employee_selection == "employee"
            and not self.employee_id
        ):

            raise ValidationError(
                "Please select an employee."
            )

        # ------------------------------------------------------
        # VALIDATE DATES
        # ------------------------------------------------------

        if (
            self.date_from
            and self.date_to
            and self.date_from > self.date_to
        ):

            raise ValidationError(
                "From Date cannot be later than To Date."
            )

        # ======================================================
        # CREATE EXCEL FILE
        # ======================================================

        output = io.BytesIO()

        workbook = xlsxwriter.Workbook(
            output,
            {
                "in_memory": True,
            }
        )

        sheet = workbook.add_worksheet(
            "Commission Report"
        )

        # ======================================================
        # PAGE SETTINGS
        # ======================================================

        sheet.set_landscape()

        sheet.fit_to_pages(
            1,
            0,
        )

        sheet.set_margins(
            left=0.25,
            right=0.25,
            top=0.50,
            bottom=0.50,
        )

        sheet.set_paper(9)

        sheet.set_default_row(20)

        sheet.hide_gridlines(2)

        # ======================================================
        # FORMATS
        # ======================================================

        title_format = workbook.add_format({
            "bold": True,
            "font_size": 20,
            "font_name": "Arial",
            "font_color": "#212529",
            "align": "left",
            "valign": "vcenter",
        })

        subtitle_format = workbook.add_format({
            "font_size": 10,
            "font_name": "Arial",
            "font_color": "#777777",
            "align": "left",
            "valign": "vcenter",
        })

        detail_label_format = workbook.add_format({
            "bold": True,
            "font_size": 10,
            "font_name": "Arial",
            "font_color": "#555555",
            "align": "right",
            "valign": "vcenter",
        })

        detail_value_format = workbook.add_format({
            "font_size": 10,
            "font_name": "Arial",
            "font_color": "#212529",
            "align": "left",
            "valign": "vcenter",
        })

        employee_format = workbook.add_format({
            "bold": True,
            "font_size": 14,
            "font_name": "Arial",
            "font_color": "#FFFFFF",
            "bg_color": "#343A40",
            "align": "left",
            "valign": "vcenter",
        })

        header_format = workbook.add_format({
            "bold": True,
            "font_size": 10,
            "font_name": "Arial",
            "font_color": "#212529",
            "bg_color": "#EEEEEE",
            "border": 1,
            "border_color": "#CCCCCC",
            "align": "center",
            "valign": "vcenter",
            "text_wrap": True,
        })

        product_format = workbook.add_format({
            "font_size": 10,
            "font_name": "Arial",
            "border": 1,
            "border_color": "#DDDDDD",
            "align": "left",
            "valign": "vcenter",
        })

        date_format = workbook.add_format({
            "font_size": 10,
            "font_name": "Arial",
            "border": 1,
            "border_color": "#DDDDDD",
            "align": "center",
            "valign": "vcenter",
        })

        quantity_format = workbook.add_format({
            "font_size": 10,
            "font_name": "Arial",
            "border": 1,
            "border_color": "#DDDDDD",
            "align": "center",
            "valign": "vcenter",
            "num_format": "0.00",
        })

        money_format = workbook.add_format({
            "font_size": 10,
            "font_name": "Arial",
            "border": 1,
            "border_color": "#DDDDDD",
            "align": "right",
            "valign": "vcenter",
            "num_format": '#,##0.00 "TSh"',
        })

        total_label_format = workbook.add_format({
            "bold": True,
            "font_size": 10,
            "font_name": "Arial",
            "bg_color": "#F3F3F3",
            "border": 1,
            "border_color": "#CCCCCC",
            "align": "right",
            "valign": "vcenter",
        })

        total_money_format = workbook.add_format({
            "bold": True,
            "font_size": 10,
            "font_name": "Arial",
            "bg_color": "#F3F3F3",
            "border": 1,
            "border_color": "#CCCCCC",
            "align": "right",
            "valign": "vcenter",
            "num_format": '#,##0.00 "TSh"',
        })

        grand_total_label_format = workbook.add_format({
            "bold": True,
            "font_size": 13,
            "font_name": "Arial",
            "font_color": "#212529",
            "top": 2,
            "top_color": "#343A40",
            "align": "left",
            "valign": "vcenter",
        })

        grand_total_header_format = workbook.add_format({
            "bold": True,
            "font_size": 9,
            "font_name": "Arial",
            "font_color": "#555555",
            "top": 2,
            "top_color": "#343A40",
            "align": "right",
            "valign": "vcenter",
        })

        grand_total_money_format = workbook.add_format({
            "bold": True,
            "font_size": 12,
            "font_name": "Arial",
            "font_color": "#212529",
            "top": 2,
            "top_color": "#343A40",
            "align": "right",
            "valign": "vcenter",
            "num_format": '#,##0.00 "TSh"',
        })

        no_data_format = workbook.add_format({
            "bold": True,
            "font_size": 12,
            "font_name": "Arial",
            "font_color": "#777777",
            "align": "center",
            "valign": "vcenter",
        })

        footer_format = workbook.add_format({
            "font_size": 9,
            "font_name": "Arial",
            "font_color": "#888888",
            "align": "center",
            "valign": "vcenter",
        })

        # ======================================================
        # COLUMN WIDTHS
        # ======================================================

        sheet.set_column(0, 0, 32)
        sheet.set_column(1, 1, 20)
        sheet.set_column(2, 2, 13)
        sheet.set_column(3, 3, 18)
        sheet.set_column(4, 4, 20)
        sheet.set_column(5, 5, 20)

        # ======================================================
        # GET DATA
        # ======================================================

        (
            employees,
            grand_total_price,
            grand_total_commission,
        ) = self._get_employee_data()

        # ======================================================
        # REPORT HEADER
        # ======================================================

        row = 0

        sheet.merge_range(
            row,
            0,
            row,
            5,
            "Employee Commission Report",
            title_format,
        )

        sheet.set_row(row, 30)

        row += 1

        sheet.merge_range(
            row,
            0,
            row,
            5,
            "Employee commission performance report",
            subtitle_format,
        )

        row += 2

        # ======================================================
        # REPORT DETAILS
        # ======================================================

        selected_employee_name = (

            self.employee_id.name

            if (
                self.employee_selection == "employee"
                and self.employee_id
            )

            else "All Employees"
        )

        selected_pos_name = (

            self.pos_config_id.name
            if self.pos_config_id
            else "All Point of Sales"
        )

        # ------------------------------------------------------
        # EMPLOYEE
        # ------------------------------------------------------

        sheet.write(
            row,
            2,
            "Employee:",
            detail_label_format,
        )

        sheet.merge_range(
            row,
            3,
            row,
            5,
            selected_employee_name,
            detail_value_format,
        )

        row += 1

        # ------------------------------------------------------
        # POINT OF SALE
        # ------------------------------------------------------

        sheet.write(
            row,
            2,
            "Point of Sale:",
            detail_label_format,
        )

        sheet.merge_range(
            row,
            3,
            row,
            5,
            selected_pos_name,
            detail_value_format,
        )

        row += 1

        # ------------------------------------------------------
        # FROM DATE
        # ------------------------------------------------------

        sheet.write(
            row,
            2,
            "From:",
            detail_label_format,
        )

        sheet.merge_range(
            row,
            3,
            row,
            5,
            str(self.date_from),
            detail_value_format,
        )

        row += 1

        # ------------------------------------------------------
        # TO DATE
        # ------------------------------------------------------

        sheet.write(
            row,
            2,
            "To:",
            detail_label_format,
        )

        sheet.merge_range(
            row,
            3,
            row,
            5,
            str(self.date_to),
            detail_value_format,
        )

        row += 2

        # ======================================================
        # EMPLOYEE SECTIONS
        # ======================================================

        for emp in employees.values():

            sheet.merge_range(
                row,
                0,
                row,
                5,
                "Employee: " + emp["name"],
                employee_format,
            )

            sheet.set_row(row, 26)

            row += 1

            headers = [
                "Product",
                "Order Date",
                "Quantity",
                "Unit Price",
                "Total Amount",
                "Commission",
            ]

            for col, header in enumerate(headers):

                sheet.write(
                    row,
                    col,
                    header,
                    header_format,
                )

            sheet.set_row(row, 25)

            row += 1

            # --------------------------------------------------
            # EMPLOYEE LINES
            # --------------------------------------------------

            for line in emp["lines"]:

                product_name = (
                    line.product_id.name
                    if line.product_id
                    else ""
                )

                sheet.write(
                    row,
                    0,
                    product_name,
                    product_format,
                )

                order_date = ""

                if (
                    line.order_id
                    and line.order_id.date_order
                ):

                    order_date = (
                        line.order_id.date_order.strftime(
                            "%d/%m/%Y %H:%M:%S"
                        )
                    )

                sheet.write(
                    row,
                    1,
                    order_date,
                    date_format,
                )

                sheet.write_number(
                    row,
                    2,
                    line.qty or 0.0,
                    quantity_format,
                )

                sheet.write_number(
                    row,
                    3,
                    line.price_unit or 0.0,
                    money_format,
                )

                line_total_price = (
                    (line.qty or 0.0)
                    *
                    (line.price_unit or 0.0)
                )

                sheet.write_number(
                    row,
                    4,
                    line_total_price,
                    money_format,
                )

                sheet.write_number(
                    row,
                    5,
                    line.commission_amount or 0.0,
                    money_format,
                )

                sheet.set_row(row, 22)

                row += 1

            # --------------------------------------------------
            # EMPLOYEE TOTAL
            # --------------------------------------------------

            sheet.merge_range(
                row,
                0,
                row,
                3,
                "Employee Total",
                total_label_format,
            )

            sheet.write_number(
                row,
                4,
                emp["total_price"],
                total_money_format,
            )

            sheet.write_number(
                row,
                5,
                emp["total_commission"],
                total_money_format,
            )

            sheet.set_row(row, 25)

            row += 2

        # ======================================================
        # GRAND TOTAL
        # ======================================================

        if employees:

            sheet.merge_range(
                row,
                0,
                row,
                2,
                "GRAND TOTAL",
                grand_total_label_format,
            )

            sheet.write(
                row,
                3,
                "TOTAL AMOUNT",
                grand_total_header_format,
            )

            sheet.write_number(
                row,
                4,
                grand_total_price,
                grand_total_money_format,
            )

            sheet.write_number(
                row,
                5,
                grand_total_commission,
                grand_total_money_format,
            )

            sheet.set_row(row, 30)

            row += 2

        else:

            sheet.merge_range(
                row,
                0,
                row,
                5,
                "No commission data found for the selected criteria.",
                no_data_format,
            )

            sheet.set_row(row, 30)

            row += 2

        # ======================================================
        # FOOTER
        # ======================================================

        sheet.merge_range(
            row,
            0,
            row,
            5,
            "Employee Commission Report | Generated by Odoo",
            footer_format,
        )

        # ======================================================
        # PRINT AREA
        # ======================================================

        sheet.print_area(
            0,
            0,
            row,
            5,
        )

        # ======================================================
        # HEADER / FOOTER
        # ======================================================

        sheet.set_header(
            "&LEmployee Commission Report"
            "&RPage &P of &N"
        )

        sheet.set_footer(
            "&CGenerated by Odoo"
        )

        # ======================================================
        # CLOSE WORKBOOK
        # ======================================================

        workbook.close()

        output.seek(0)

        file_data = base64.b64encode(
            output.read()
        )

        # ======================================================
        # CREATE ATTACHMENT
        # ======================================================

        attachment = self.env[
            "ir.attachment"
        ].create({

            "name":
                "Employee_Commission_Report.xlsx",

            "type":
                "binary",

            "datas":
                file_data,

            "mimetype":
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",

        })

        # ======================================================
        # DOWNLOAD EXCEL
        # ======================================================

        return {

            "type":
                "ir.actions.act_url",

            "url":
                "/web/content/%s?download=true"
                % attachment.id,

            "target":
                "self",

        }