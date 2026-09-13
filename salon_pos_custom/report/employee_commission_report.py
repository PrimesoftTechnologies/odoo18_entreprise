from datetime import timedelta

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
        # SEARCH DOMAIN FOR POS COMMISSION LINES
        # ==========================================================

        domain = []

        # ----------------------------------------------------------
        # EMPLOYEE
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
        # POINT OF SALE
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

            date_from_datetime = fields.Datetime.to_datetime(
                date_from
            )

            domain.append(
                (
                    "order_id.date_order",
                    ">=",
                    date_from_datetime,
                )
            )

        # ----------------------------------------------------------
        # TO DATE
        #
        # +1 day makes the selected end date inclusive.
        # ----------------------------------------------------------

        if date_to:

            date_to_datetime = (
                fields.Datetime.to_datetime(
                    date_to
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

        # ----------------------------------------------------------
        # ONLY LINES WITH EMPLOYEE
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
        # GET EMPLOYEE IDS
        # ==========================================================

        employee_ids = lines.mapped(
            "employee_id"
        ).ids

        # ==========================================================
        # GET ALL PAID PAYOUTS
        #
        # IMPORTANT:
        #
        # We no longer use ONLY the latest payout.
        #
        # We get ALL PAID payouts for each employee.
        #
        # Example:
        #
        # Payout 1:
        # Deduction = 5,000
        #
        # Payout 2:
        # Deduction = 7,000
        #
        # Total deductions = 12,000
        #
        # POS commission = 12,000
        #
        # Current balance = 0
        # ==========================================================

        payout_map = {}

        if employee_ids:

            payout_records = self.env[
                "salon.commission.payout"
            ].search(
                [
                    (
                        "employee_id",
                        "in",
                        employee_ids,
                    ),
                    (
                        "state",
                        "=",
                        "paid",
                    ),
                ],
                order="employee_id, id asc",
            )

            # ------------------------------------------------------
            # GROUP PAYOUTS BY EMPLOYEE
            # ------------------------------------------------------

            for payout in payout_records:

                employee_id_value = (
                    payout.employee_id.id
                )

                if employee_id_value not in payout_map:

                    payout_map[
                        employee_id_value
                    ] = []

                payout_map[
                    employee_id_value
                ].append(payout)

        # ==========================================================
        # GROUP POS LINES BY EMPLOYEE
        # ==========================================================

        for line in lines:

            employee = line.employee_id

            if not employee:
                continue

            employee_id_value = employee.id

            # ------------------------------------------------------
            # CREATE EMPLOYEE RECORD
            # ------------------------------------------------------

            if employee_id_value not in employees:

                employees[
                    employee_id_value
                ] = {

                    "name":
                        employee.name,

                    "lines":
                        [],

                    # Total POS sales value
                    "total_price":
                        0.0,

                    # Total commission earned from POS
                    # within the selected report period.
                    "total_commission":
                        0.0,

                    # Total amount deducted through
                    # ALL PAID payout records.
                    "advance_deduction":
                        0.0,

                    # Current commission balance.
                    "current_commission":
                        0.0,

                    # Net commission.
                    "net_commission":
                        0.0,
                }

            # ------------------------------------------------------
            # ADD POS LINE
            # ------------------------------------------------------

            employees[
                employee_id_value
            ][
                "lines"
            ].append(line)

            # ------------------------------------------------------
            # TOTAL SALES VALUE
            # ------------------------------------------------------

            line_total_price = (
                (line.qty or 0.0)
                *
                (line.price_unit or 0.0)
            )

            employees[
                employee_id_value
            ][
                "total_price"
            ] += line_total_price

            # ------------------------------------------------------
            # TOTAL POS COMMISSION
            # ------------------------------------------------------

            employees[
                employee_id_value
            ][
                "total_commission"
            ] += (
                line.commission_amount
                or 0.0
            )

        # ==========================================================
        # CALCULATE PAYOUTS AND CURRENT BALANCE
        # ==========================================================

        for emp_id, emp_data in employees.items():

            # ------------------------------------------------------
            # GET ALL PAID PAYOUTS FOR THIS EMPLOYEE
            # ------------------------------------------------------

            employee_payouts = payout_map.get(
                emp_id,
                []
            )

            # ------------------------------------------------------
            # TOTAL DEDUCTIONS FROM ALL PAID PAYOUTS
            # ------------------------------------------------------

            total_paid_deductions = sum(
                (
                    payout.advance_deduction
                    or 0.0
                )
                for payout in employee_payouts
            )

            # ------------------------------------------------------
            # CURRENT COMMISSION
            #
            # POS commission:
            #
            # Example:
            # 12,000
            #
            # Less all paid deductions:
            #
            # 5,000 + 7,000 = 12,000
            #
            # Balance:
            #
            # 12,000 - 12,000 = 0
            # ------------------------------------------------------

            current_commission = (
                emp_data[
                    "total_commission"
                ]
                -
                total_paid_deductions
            )

            # ------------------------------------------------------
            # NEVER ALLOW NEGATIVE BALANCE
            # ------------------------------------------------------

            if current_commission < 0:

                current_commission = 0.0

            # ------------------------------------------------------
            # SAVE TOTAL DEDUCTIONS
            # ------------------------------------------------------

            emp_data[
                "advance_deduction"
            ] = total_paid_deductions

            # ------------------------------------------------------
            # SAVE CURRENT BALANCE
            # ------------------------------------------------------

            emp_data[
                "current_commission"
            ] = current_commission

            # ------------------------------------------------------
            # NET COMMISSION
            # ------------------------------------------------------

            emp_data[
                "net_commission"
            ] = current_commission

        # ==========================================================
        # GRAND TOTAL SALES
        # ==========================================================

        grand_total_price = sum(
            employee[
                "total_price"
            ]
            for employee in employees.values()
        )

        # ==========================================================
        # GRAND TOTAL POS COMMISSION
        #
        # This is the commission earned from POS transactions.
        # ==========================================================

        grand_total_earned_commission = sum(
            employee[
                "total_commission"
            ]
            for employee in employees.values()
        )

        # ==========================================================
        # GRAND TOTAL DEDUCTIONS
        # ==========================================================

        grand_total_deductions = sum(
            employee[
                "advance_deduction"
            ]
            for employee in employees.values()
        )

        # ==========================================================
        # GRAND TOTAL CURRENT BALANCE
        # ==========================================================

        grand_total_commission = sum(
            employee[
                "current_commission"
            ]
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

            # ------------------------------------------------------
            # GRAND TOTALS
            # ------------------------------------------------------

            "grand_total_price":
                grand_total_price,

            # Current balance / net commission
            "grand_total_commission":
                grand_total_commission,

            # Additional totals available to QWeb
            "grand_total_earned_commission":
                grand_total_earned_commission,

            "grand_total_deductions":
                grand_total_deductions,
        }