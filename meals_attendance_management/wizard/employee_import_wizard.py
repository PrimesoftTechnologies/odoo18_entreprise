import base64
import csv
import io
import logging

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

HEADER_ALIASES = {
    'employee_no': {'employee no', 'employee number', 'emp no', 'employee id', 'staff no', 'code', 'id', 'no'},
    'name': {'name', 'employee name', 'full name', 'employee'},
    'department': {'department', 'dept', 'department name'},
    'job_title': {'job title', 'job', 'position', 'title'},
}


def _cell_to_str(value):
    if value is None:
        return ''
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value).strip()


class MealsEmployeeImportWizard(models.TransientModel):
    _name = 'meals.employee.import.wizard'
    _description = 'Import Customer Employees'

    customer_id = fields.Many2one('res.partner', string='Customer', required=True,
                                  domain=[('is_meal_customer', '=', True)])
    file = fields.Binary(string='CSV / XLSX File', required=True)
    filename = fields.Char()
    create_departments = fields.Boolean(
        string='Create missing departments', default=True,
        help="If unticked, rows whose department does not exist are rejected.")
    update_existing = fields.Boolean(
        string='Update existing employees', default=True,
        help="Existing = same Employee No. for this customer. If unticked they are skipped.")
    state = fields.Selection([('start', 'Start'), ('done', 'Done')], default='start')
    created_count = fields.Integer(readonly=True)
    updated_count = fields.Integer(readonly=True)
    skipped_count = fields.Integer(readonly=True)
    error_count = fields.Integer(readonly=True)
    result_log = fields.Text(readonly=True)

    # ---------- file parsing ----------
    def _read_rows(self):
        raw = base64.b64decode(self.file)
        fname = (self.filename or '').lower()
        if fname.endswith('.csv'):
            text = raw.decode('utf-8-sig', errors='replace')
            try:
                dialect = csv.Sniffer().sniff(text[:2048], delimiters=',;\t')
            except csv.Error:
                dialect = csv.excel
            return [[_cell_to_str(c) for c in row] for row in csv.reader(io.StringIO(text), dialect)]
        if fname.endswith(('.xlsx', '.xlsm')):
            try:
                import openpyxl
            except ImportError:
                raise UserError(_("Python library 'openpyxl' is required to read XLSX files. "
                                  "Install it or upload a CSV file."))
            wb = openpyxl.load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
            ws = wb.active
            return [[_cell_to_str(c) for c in row] for row in ws.iter_rows(values_only=True)]
        raise UserError(_("Unsupported file type. Please upload a .csv or .xlsx file."))

    @staticmethod
    def _norm(header):
        return (header or '').strip().lower().replace('_', ' ')

    # ---------- main action ----------
    def action_import(self):
        self.ensure_one()
        rows = [r for r in self._read_rows() if any(r)]
        if len(rows) < 2:
            raise UserError(_("The file has no data rows."))

        header = [self._norm(h) for h in rows[0]]
        col = {}
        for key, aliases in HEADER_ALIASES.items():
            for idx, h in enumerate(header):
                if h in aliases:
                    col[key] = idx
                    break
        missing = [k for k in ('employee_no', 'name') if k not in col]
        if missing:
            raise UserError(_("Missing required column(s): %s. Expected columns: "
                              "employee_no, name, department, job_title.", ', '.join(missing)))

        def cell(row, key):
            idx = col.get(key)
            return row[idx].strip() if idx is not None and idx < len(row) else ''

        customer = self.customer_id
        Employee = self.env['hr.employee'].with_context(active_test=False)
        Department = self.env['hr.department']

        def load_depts():
            return {d.name.strip().lower(): d
                    for d in Department.search([('meal_customer_id', '=', customer.id)])}

        dept_cache = load_depts()
        existing = {e.meal_employee_no: e for e in Employee.search(
            [('meal_customer_id', '=', customer.id), ('meal_employee_no', '!=', False)])}

        created = updated = skipped = 0
        errors, seen = [], set()

        for n, row in enumerate(rows[1:], start=2):
            code, name = cell(row, 'employee_no'), cell(row, 'name')
            dept_name, job = cell(row, 'department'), cell(row, 'job_title')
            if not code or not name:
                errors.append(_("Row %s: Employee No. and Name are required.", n))
                continue
            if code in seen:
                errors.append(_("Row %s: Employee No. %s is duplicated in the file.", n, code))
                continue
            seen.add(code)
            try:
                with self.env.cr.savepoint():
                    dept = Department
                    if dept_name:
                        dept = dept_cache.get(dept_name.lower())
                        if not dept:
                            if not self.create_departments:
                                raise UserError(_("Department '%s' does not exist.", dept_name))
                            dept = Department.create(
                                {'name': dept_name, 'meal_customer_id': customer.id})
                            dept_cache[dept_name.lower()] = dept
                    emp = existing.get(code)
                    if emp:
                        if not self.update_existing:
                            skipped += 1
                            continue
                        vals = {'name': name, 'active': True}
                        if dept:
                            vals['department_id'] = dept.id
                        if job:
                            vals['job_title'] = job
                        emp.write(vals)
                        updated += 1
                    else:
                        existing[code] = Employee.create({
                            'name': name,
                            'meal_employee_no': code,
                            'meal_customer_id': customer.id,
                            'is_meal_employee': True,
                            'department_id': dept.id if dept else False,
                            'job_title': job or False,
                        })
                        created += 1
            except Exception as e:  # noqa: BLE001 - report any row problem, keep importing
                _logger.info("Meals import row %s failed: %s", n, e)
                errors.append(_("Row %(row)s (%(code)s): %(err)s", row=n, code=code, err=str(e)))
                dept_cache = load_depts()  # cache may contain rolled-back departments

        log = [_("Created: %s | Updated: %s | Skipped: %s | Errors: %s",
                 created, updated, skipped, len(errors))]
        log += errors
        self.write({
            'state': 'done', 'created_count': created, 'updated_count': updated,
            'skipped_count': skipped, 'error_count': len(errors), 'result_log': '\n'.join(log),
        })
        return {
            'type': 'ir.actions.act_window', 'res_model': self._name, 'res_id': self.id,
            'view_mode': 'form', 'target': 'new',
        }

    def action_view_employees(self):
        self.ensure_one()
        return self.customer_id.action_view_meal_employees()
