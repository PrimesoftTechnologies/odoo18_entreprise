from odoo import api, fields, models


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    attendance_bic_ids = fields.One2many(
        'payslip.attendance.bic', string='Attendance (BIC)',
        compute='_compute_attendance_bic_ids')
    attendance_bic_days = fields.Integer(
        string='Attendance Days (BIC)', compute='_compute_attendance_bic_ids')

    def _get_attendance_bic_records(self):
        self.ensure_one()
        if not (self.employee_id and self.date_from and self.date_to):
            return self.env['payslip.attendance.bic']
        return self.env['payslip.attendance.bic'].search([
            ('employee_id', '=', self.employee_id.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ], order='date')

    @api.depends('employee_id', 'date_from', 'date_to')
    def _compute_attendance_bic_ids(self):
        for slip in self:
            records = slip._get_attendance_bic_records()
            slip.attendance_bic_ids = records
            slip.attendance_bic_days = len(set(records.mapped('date')))

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
