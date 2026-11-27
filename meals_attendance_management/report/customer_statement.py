from odoo import _, api, fields, models
from odoo.tools.misc import format_date


class ReportCustomerStatement(models.AbstractModel):
    _name = 'report.meals_attendance_management.report_customer_statement'
    _description = 'Customer Meals Statement'

    @staticmethod
    def _matrix(lines, meal_types, key_func, label_func, sub_func=None):
        rows = {}
        for line in lines:
            key = key_func(line)
            row = rows.setdefault(key, {
                'label': label_func(line),
                'sub': sub_func(line) if sub_func else '',
                'counts': dict.fromkeys(meal_types.ids, 0),
                'qty': 0, 'amount': 0.0,
            })
            row['counts'][line.meal_type_id.id] += 1
            row['qty'] += 1
            row['amount'] += line.unit_price
        return sorted(rows.values(), key=lambda r: (r['sub'], r['label']))

    @api.model
    def _get_report_values(self, docids, data=None):
        data = data or {}
        customer = self.env['res.partner'].browse(data.get('customer_id'))
        date_from = fields.Date.to_date(data.get('date_from'))
        date_to = fields.Date.to_date(data.get('date_to'))
        domain = [
            ('customer_id', '=', customer.id), ('date', '>=', date_from), ('date', '<=', date_to),
            ('state', '=', 'confirmed'), ('attended', '=', True),
        ]
        if data.get('meal_type_ids'):
            domain.append(('meal_type_id', 'in', data['meal_type_ids']))
        lines = self.env['meals.attendance.line'].search(domain)
        meal_types = lines.meal_type_id.sorted('sequence')

        meal_summary = []
        for mt in meal_types:
            mlines = lines.filtered(lambda l, mt=mt: l.meal_type_id == mt)
            meal_summary.append({'name': mt.name, 'qty': len(mlines),
                                 'amount': sum(mlines.mapped('unit_price'))})

        no_dept = _('No Department')
        dept_rows = self._matrix(
            lines, meal_types,
            key_func=lambda l: l.department_id.id,
            label_func=lambda l: l.department_id.name or no_dept)
        employee_rows = self._matrix(
            lines, meal_types,
            key_func=lambda l: l.employee_id.id,
            label_func=lambda l: "%s - %s" % (l.employee_id.meal_employee_no or '', l.employee_id.name),
            sub_func=lambda l: l.department_id.name or no_dept)

        return {
            'doc_ids': docids,
            'doc_model': 'meals.report.wizard',
            'customer': customer,
            'date_from': format_date(self.env, date_from),
            'date_to': format_date(self.env, date_to),
            'meal_types': meal_types,
            'meal_summary': meal_summary,
            'dept_rows': dept_rows,
            'employee_rows': employee_rows,
            'total_qty': len(lines),
            'total_amount': sum(lines.mapped('unit_price')),
            'meal_totals': {mt.id: len(lines.filtered(lambda l, mt=mt: l.meal_type_id == mt))
                            for mt in meal_types},
            'currency': self.env.company.currency_id,
        }
