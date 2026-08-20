from odoo import api, fields, models

class EmployeeCommissionReport(models.AbstractModel):

    _name = "report.salon_pos_custom.employee_commission_template"
    _description = "Employee Commission Report"

    @api.model
    def _get_report_values(self, docids, data=None):

        # ==========================================================
        # WIZARD
        # ==========================================================

        wizard = self.env[
            "commission.report.wizard"
        ].browse(docids)

        employees = {}

        date_from = False
        date_to = False

        selected_employee = False
        selected_pos = False

        employee_selection = "all"
        employee_id = False
        pos_config_id = False

        # ==========================================================
        # GET DATA FROM WIZARD
        # ==========================================================

        if data:

            employee_selection = data.get(
                "employee_selection",
                "all",
            )

            employee_id = data.get(
                "employee_id",
                False,
            )

            pos_config_id = data.get(
                "pos_config_id",
                False,
            )

            date_from = data.get(
                "date_from",
                False,
            )

            date_to = data.get(
                "date_to",
                False,
            )

        # ==========================================================
        # SELECTED EMPLOYEE
        # ==========================================================

        if (
            employee_selection == "employee"
            and employee_id
        ):

            employee = self.env[
                "hr.employee"
            ].browse(employee_id)

            if employee.exists():

                selected_employee = employee.name

        else:

            selected_employee = "All Employees"

        # ==========================================================
        # SELECTED POINT OF SALE
        # ==========================================================

        if pos_config_id:

            pos_config = self.env[
                "pos.config"
            ].browse(pos_config_id)

            if pos_config.exists():

                selected_pos = pos_config.name

        else:

            selected_pos = "All Point of Sales"

        # ==========================================================
        # SEARCH DOMAIN
        # ==========================================================

        domain = []

        # ----------------------------------------------------------
        # EMPLOYEE FILTER
        # ----------------------------------------------------------

        if (
            employee_selection == "employee"
            and employee_id
        ):

            domain.append(
                (
                    "employee_id",
                    "=",
                    employee_id,
                )
            )

        # ----------------------------------------------------------
        # POINT OF SALE FILTER
        # ----------------------------------------------------------

        if pos_config_id:

            domain.append(
                (
                    "order_id.session_id.config_id",
                    "=",
                    pos_config_id,
                )
            )

        # ----------------------------------------------------------
        # FROM DATE
        # ----------------------------------------------------------

        if date_from:

            domain.append(
                (
                    "order_id.date_order",
                    ">=",
                    date_from,
                )
            )

        # ----------------------------------------------------------
        # TO DATE
        #
        # Include the complete selected day.
        # ----------------------------------------------------------

        if date_to:

            domain.append(
                (
                    "order_id.date_order",
                    "<",
                    fields.Datetime.to_datetime(
                        date_to
                    ) + __import__("datetime").timedelta(days=1),
                )
            )

        # ----------------------------------------------------------
        # ONLY EMPLOYEE COMMISSION LINES
        # ----------------------------------------------------------

        domain.append(
            (
                "employee_id",
                "!=",
                False,
            )
        )

        # ----------------------------------------------------------
        # ONLY POSITIVE COMMISSION
        # ----------------------------------------------------------

        domain.append(
            (
                "commission_amount",
                ">",
                0,
            )
        )

        # ==========================================================
        # GET POS ORDER LINES
        # ==========================================================

        lines = self.env[
            "pos.order.line"
        ].search(
            domain,
            order="employee_id, order_id, id",
        )

        # ==========================================================
        # GROUP LINES BY EMPLOYEE
        # ==========================================================

        for line in lines:

            employee = line.employee_id

            if not employee:
                continue

            # ------------------------------------------------------
            # CREATE EMPLOYEE GROUP
            # ------------------------------------------------------

            if employee.id not in employees:

                employees[
                    employee.id
                ] = {

                    "name":
                        employee.name,

                    "lines":
                        [],

                    "total_price":
                        0.0,

                    "total_commission":
                        0.0,

                }

            # ------------------------------------------------------
            # ADD LINE
            # ------------------------------------------------------

            employees[
                employee.id
            ][
                "lines"
            ].append(line)

            # ------------------------------------------------------
            # TOTAL PRICE
            # ------------------------------------------------------

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

            # ------------------------------------------------------
            # TOTAL COMMISSION
            # ------------------------------------------------------

            employees[
                employee.id
            ][
                "total_commission"
            ] += (
                line.commission_amount
                or 0.0
            )

        # ==========================================================
        # GRAND TOTAL PRICE
        # ==========================================================

        grand_total_price = sum(
            employee["total_price"]
            for employee in employees.values()
        )

        # ==========================================================
        # GRAND TOTAL COMMISSION
        # ==========================================================

        grand_total_commission = sum(
            employee["total_commission"]
            for employee in employees.values()
        )

        # ==========================================================
        # RETURN REPORT DATA
        # ==========================================================

        return {

            "doc_ids":
                docids,

            "doc_model":
                "commission.report.wizard",

            "docs":
                wizard,

            "employees":
                employees,

            "date_from":
                date_from,

            "date_to":
                date_to,

            "selected_employee":
                selected_employee,

            "selected_pos":
                selected_pos,

            "employee_selection":
                employee_selection,

            "pos_config_id":
                pos_config_id,

            "grand_total_price":
                grand_total_price,

            "grand_total_commission":
                grand_total_commission,

        }