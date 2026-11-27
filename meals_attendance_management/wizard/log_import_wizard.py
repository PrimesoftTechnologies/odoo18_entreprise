import base64
import csv
import io
from datetime import date, datetime, time, timedelta

from odoo import _, fields, models
from odoo.exceptions import UserError

# dd/mm/yyyy is tried before mm/dd/yyyy (East Africa convention)
DATETIME_FORMATS = [
    '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y/%m/%d %H:%M:%S', '%Y/%m/%d %H:%M',
    '%d/%m/%Y %H:%M:%S', '%d/%m/%Y %H:%M', '%d-%m-%Y %H:%M:%S', '%d-%m-%Y %H:%M',
    '%d/%m/%Y %I:%M:%S %p', '%d/%m/%Y %I:%M %p', '%m/%d/%Y %H:%M:%S', '%m/%d/%Y %I:%M:%S %p',
    '%d.%m.%Y %H:%M:%S', '%d.%m.%Y %H:%M',
]
DATE_FORMATS = ['%Y-%m-%d', '%Y/%m/%d', '%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y', '%m/%d/%Y']
TIME_FORMATS = ['%H:%M:%S', '%H:%M', '%I:%M:%S %p', '%I:%M %p']

HEADER_ALIASES = {
    'employee_no': {'employee no', 'employee number', 'emp no', 'employee id', 'person id', 'user id',
                    'userid', 'badge', 'badge no', 'card no', 'staff no', 'ac no', 'code', 'id', 'no'},
    'datetime': {'datetime', 'date time', 'date/time', 'timestamp', 'punch time', 'scan time',
                 'check time', 'check in', 'clock in'},
    'date': {'date', 'scan date', 'punch date'},
    'time': {'time'},
}
MAX_LOGGED_ERRORS = 200


def _norm_header(value):
    return str(value or '').strip().lower().replace('_', ' ').replace('-', ' ')


def _to_str(value):
    if value is None:
        return ''
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value).strip()


def _norm_code(value):
    return _to_str(value).lower().lstrip('0')


def _excel_serial(value):
    return datetime(1899, 12, 30) + timedelta(days=float(value))


def _parse(value, formats):
    text = _to_str(value)
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def to_datetime(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, time())
    if isinstance(value, (int, float)) and value > 1:
        return _excel_serial(value)
    return _parse(value, DATETIME_FORMATS)


def to_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)) and value > 1:
        return _excel_serial(value).date()
    parsed = _parse(value, DATE_FORMATS) or _parse(value, DATETIME_FORMATS)
    return parsed.date() if parsed else None


def to_time(value):
    if isinstance(value, datetime):
        return value.time()
    if isinstance(value, time):
        return value
    if isinstance(value, (int, float)) and 0 <= value < 1:
        return (datetime(2000, 1, 1) + timedelta(days=float(value))).time()
    parsed = _parse(value, TIME_FORMATS) or _parse(value, DATETIME_FORMATS)
    return parsed.time() if parsed else None


class MealsLogImportWizard(models.TransientModel):
    _name = 'meals.log.import.wizard'
    _description = 'Import Attendance Machine Logs'

    customer_id = fields.Many2one('res.partner', string='Customer', required=True,
                                  domain=[('is_meal_customer', '=', True)])
    file = fields.Binary(string='Excel / CSV File', required=True)
    filename = fields.Char()
    auto_confirm = fields.Boolean(
        string='Confirm sheets after import', default=True,
        help="Imported draft sheets are confirmed so they can be invoiced.")
    state = fields.Selection([('start', 'Start'), ('done', 'Done')], default='start')
    imported_count = fields.Integer(string='Meals Recorded', readonly=True)
    duplicate_count = fields.Integer(string='Duplicates Ignored', readonly=True)
    error_count = fields.Integer(string='Rejected Rows', readonly=True)
    sheet_ids = fields.Many2many('meals.attendance', string='Sheets', readonly=True)
    result_log = fields.Text(readonly=True)

    # ---------- reading ----------
    def _read_rows(self):
        raw = base64.b64decode(self.file)
        fname = (self.filename or '').lower()
        if fname.endswith('.csv'):
            text = raw.decode('utf-8-sig', errors='replace')
            try:
                dialect = csv.Sniffer().sniff(text[:2048], delimiters=',;\t')
            except csv.Error:
                dialect = csv.excel
            return [list(r) for r in csv.reader(io.StringIO(text), dialect)]
        if fname.endswith(('.xlsx', '.xlsm')):
            try:
                import openpyxl
            except ImportError:
                raise UserError(_("Python library 'openpyxl' is required to read XLSX files. "
                                  "Install it or upload a CSV file."))
            wb = openpyxl.load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
            return [list(r) for r in wb.active.iter_rows(values_only=True)]
        raise UserError(_("Unsupported file type. Please upload an .xlsx or .csv file."))

    @staticmethod
    def _find_header(rows):
        """Machine exports often have title rows: look for the header in the first 20 rows."""
        for idx, row in enumerate(rows[:20]):
            col = {}
            for pos, cell in enumerate(row):
                head = _norm_header(cell)
                for key, aliases in HEADER_ALIASES.items():
                    if head in aliases and key not in col:
                        col[key] = pos
            if 'time' in col and 'date' not in col and 'datetime' not in col:
                col['datetime'] = col.pop('time')   # single "Time" column holding date + time
            if 'employee_no' in col and ('datetime' in col or ('date' in col and 'time' in col)):
                return idx, col
        return None, None

    @staticmethod
    def _match_meal(meal_types, hour):
        for meal in meal_types:
            start, end = meal.start_time, meal.end_time
            if start == end:
                continue  # times not configured
            if (start <= hour <= end) if start < end else (hour >= start or hour <= end):
                return meal
        return None

    # ---------- main action ----------
    def action_import(self):
        self.ensure_one()
        customer = self.customer_id
        rows = [r for r in self._read_rows() if any(c not in (None, '') for c in r)]
        head_idx, col = self._find_header(rows)
        if head_idx is None:
            raise UserError(_(
                "Could not find the header row. The file needs an employee number column "
                "(e.g. 'employee_no', 'Person ID') and a date/time column (e.g. 'datetime') "
                "or separate 'date' and 'time' columns."))

        meal_types = self.env['meals.type'].search(
            [('customer_id', '=', customer.id)], order='sequence, start_time')
        if not any(m.start_time != m.end_time for m in meal_types):
            raise UserError(_("Customer %s has no meal types with From/To times. "
                              "Configure them first (Configuration → Meal Types).", customer.name))

        employees = {}
        for emp in self.env['hr.employee'].search(
                [('meal_customer_id', '=', customer.id), ('meal_employee_no', '!=', False)]):
            employees[_norm_code(emp.meal_employee_no)] = emp

        errors, scans = [], []
        for n, row in enumerate(rows[head_idx + 1:], start=head_idx + 2):
            def cell(key):
                pos = col.get(key)
                return row[pos] if pos is not None and pos < len(row) else None
            code = _to_str(cell('employee_no'))
            if not code:
                errors.append(_("Row %s: empty employee number.", n))
                continue
            emp = employees.get(_norm_code(code))
            if not emp:
                errors.append(_("Row %(n)s: employee no. '%(code)s' not found for this customer.",
                                n=n, code=code))
                continue
            if 'datetime' in col:
                stamp = to_datetime(cell('datetime'))
            else:
                d, t = to_date(cell('date')), to_time(cell('time'))
                stamp = datetime.combine(d, t) if d and t else None
            if not stamp:
                errors.append(_("Row %(n)s: invalid date/time.", n=n))
                continue
            hour = stamp.hour + stamp.minute / 60.0 + stamp.second / 3600.0
            meal = self._match_meal(meal_types, hour)
            if not meal:
                errors.append(_("Row %(n)s: %(code)s scanned at %(t)s, outside any meal time.",
                                n=n, code=code, t=stamp.strftime('%d/%m/%Y %H:%M')))
                continue
            # a night meal scanned after midnight belongs to the previous day's sheet
            sheet_date = stamp.date()
            if meal.start_time > meal.end_time and hour <= meal.end_time:
                sheet_date -= timedelta(days=1)
            scans.append((stamp, hour, emp, meal, sheet_date))

        scans.sort(key=lambda s: s[0])
        Sheet, Line = self.env['meals.attendance'], self.env['meals.attendance.line']
        sheets = {}
        if scans:
            dates = [s[4] for s in scans]
            for sheet in Sheet.search([('customer_id', '=', customer.id),
                                       ('date', '>=', min(dates)), ('date', '<=', max(dates))]):
                sheets[(sheet.meal_type_id.id, sheet.date)] = sheet
        line_map = {(l.attendance_id.id, l.employee_id.id): l
                    for l in Line.search([('attendance_id', 'in', [s.id for s in sheets.values()])])}

        imported = duplicates = 0
        touched, to_create, pending = self.env['meals.attendance'], [], set()
        for stamp, hour, emp, meal, sheet_date in scans:
            key = (meal.id, sheet_date)
            sheet = sheets.get(key)
            if not sheet:
                sheet = sheets[key] = Sheet.create({
                    'customer_id': customer.id, 'meal_type_id': meal.id, 'date': sheet_date})
            touched |= sheet
            line_key = (sheet.id, emp.id)
            line = line_map.get(line_key)
            if line_key in pending or (line and line.attended):
                duplicates += 1
                continue
            if line:
                if line.invoice_id:
                    errors.append(_("%(emp)s on %(sheet)s is already invoiced.",
                                    emp=emp.name, sheet=sheet.name))
                    continue
                line.write({'attended': True, 'scan_time': hour, 'source': 'machine'})
            else:
                to_create.append({'attendance_id': sheet.id, 'employee_id': emp.id, 'attended': True,
                                  'scan_time': hour, 'source': 'machine'})
                pending.add(line_key)
            imported += 1
        Line.create(to_create)

        if self.auto_confirm:
            touched.filtered(lambda s: s.state == 'draft' and s.attended_count).action_confirm()

        log = [_("Meals recorded: %(i)s | Duplicates ignored: %(d)s | Rejected rows: %(e)s | Sheets: %(s)s",
                 i=imported, d=duplicates, e=len(errors), s=len(touched))]
        log += errors[:MAX_LOGGED_ERRORS]
        if len(errors) > MAX_LOGGED_ERRORS:
            log.append(_("... and %s more.", len(errors) - MAX_LOGGED_ERRORS))
        self.write({
            'state': 'done', 'imported_count': imported, 'duplicate_count': duplicates,
            'error_count': len(errors), 'sheet_ids': [(6, 0, touched.ids)],
            'result_log': '\n'.join(log),
        })
        return {'type': 'ir.actions.act_window', 'res_model': self._name, 'res_id': self.id,
                'view_mode': 'form', 'target': 'new'}

    def action_view_sheets(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('Imported Sheets'),
            'res_model': 'meals.attendance', 'view_mode': 'list,form',
            'domain': [('id', 'in', self.sheet_ids.ids)],
        }
