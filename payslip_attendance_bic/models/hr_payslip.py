from datetime import timedelta

from odoo import api, fields, models


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    attendance_bic_ids = fields.One2many(
        'payslip.attendance.bic', string='Attendance (BIC)',
        compute='_compute_attendance_bic_ids')
    attendance_bic_days = fields.Integer(
        string='Attendance Days (BIC)', compute='_compute_attendance_bic_ids')
    expected_days_bic = fields.Integer(
        string='Expected Working Days', compute='_compute_attendance_bic_ids')
    meals_amount_bic = fields.Monetary(
        string='Meals Amount (BIC)', compute='_compute_attendance_bic_ids',
        currency_field='currency_id',
        help='Contract Meals Amount prorated by attendance days: '
             'Meals Amount x (Attendance Days / Expected Working Days).')

    def _get_attendance_bic_records(self):
        self.ensure_one()
        if not (self.employee_id and self.date_from and self.date_to):
            return self.env['payslip.attendance.bic']
        return self.env['payslip.attendance.bic'].search([
            ('employee_id', '=', self.employee_id.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ], order='date')

    def _get_expected_days_bic(self):
        """Working days in the period according to the contract schedule."""
        self.ensure_one()
        if not (self.date_from and self.date_to):
            return 0
        calendar = (self.contract_id.resource_calendar_id
                    or self.employee_id.resource_calendar_id)
        if calendar and calendar.attendance_ids:
            weekdays = {int(d) for d in calendar.attendance_ids.mapped('dayofweek')}
        else:
            weekdays = {0, 1, 2, 3, 4}
        count = 0
        day = self.date_from
        while day <= self.date_to:
            if day.weekday() in weekdays:
                count += 1
            day += timedelta(days=1)
        return count

    @api.depends('employee_id', 'date_from', 'date_to', 'contract_id',
                 'contract_id.meals_amount')
    def _compute_attendance_bic_ids(self):
        for slip in self:
            records = slip._get_attendance_bic_records()
            days = len(set(records.mapped('date')))
            expected = slip._get_expected_days_bic()
            slip.attendance_bic_ids = records
            slip.attendance_bic_days = days
            slip.expected_days_bic = expected
            meals = slip.contract_id.meals_amount if slip.contract_id else 0.0
            ratio = min(days / expected, 1.0) if expected else 0.0
            slip.meals_amount_bic = meals * ratio

    def _get_worked_day_lines(self, *args, **kwargs):
        """Append a worked-days line built from the BIC attendance records."""
        res = super()._get_worked_day_lines(*args, **kwargs)
        self.ensure_one()
        records = self._get_attendance_bic_records()
        days = len(set(records.mapped('date')))
        if days:
            work_type = self.env.ref(
                'payslip_attendance_bic.work_entry_type_attendance_bic',
                raise_if_not_found=False)
            if work_type:
                calendar = (self.contract_id.resource_calendar_id
                            or self.employee_id.resource_calendar_id)
                hours_per_day = (calendar.hours_per_day if calendar else 0) or 8.0
                res.append({
                    'sequence': 90,
                    'work_entry_type_id': work_type.id,
                    'number_of_days': days,
                    'number_of_hours': days * hours_per_day,
                })
        return res
