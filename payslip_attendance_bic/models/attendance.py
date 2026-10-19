from odoo import fields, models


class PayslipAttendanceBic(models.Model):
    _name = 'payslip.attendance.bic'
    _description = 'Payslip Attendance'
    _order = 'date desc, time desc, id desc'
    _rec_name = 'employee_id'

    employee_id = fields.Many2one(
        'hr.employee', string='Employee Name', required=True,
        index=True, ondelete='cascade')
    date = fields.Date(
        string='Date', required=True, index=True,
        default=fields.Date.context_today)
    time = fields.Float(string='Time', help='Time of attendance (HH:MM)')
    company_id = fields.Many2one(
        'res.company', string='Company',
        related='employee_id.company_id', store=True, readonly=True)

    _sql_constraints = [
        ('employee_date_uniq', 'unique(employee_id, date)',
         'This employee already has an attendance record for that date.'),
    ]
