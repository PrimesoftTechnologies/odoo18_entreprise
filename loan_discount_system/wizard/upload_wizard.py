# -*- coding: utf-8 -*-
import base64
import io
from datetime import date, datetime

from odoo import fields, models, _
from odoo.exceptions import UserError

ALIASES = {
    'date': {'date', 'due date', 'payment date', 'installment date', 'tarehe'},
    'principal': {'principal', 'principals', 'principal amount', 'mtaji'},
    'interest': {'interest', 'interests', 'interest amount', 'riba'},
    'payment': {'payment', 'payments', 'installment', 'instalment', 'total', 'emi', 'total payment'},
    'balance': {'balance', 'outstanding', 'outstanding balance', 'closing balance'},
}


def _norm(v):
    return str(v).strip().lower() if v is not None else ''


def _to_float(v):
    if v in (None, ''):
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace(',', '').replace(' ', '').replace('TSh', '').replace('TZS', '').strip()
    if s in ('', '-'):
        return 0.0
    if s.startswith('(') and s.endswith(')'):
        s = '-' + s[1:-1]
    return float(s)


def _to_date(v):
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v).strip()
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%m/%d/%Y', '%d.%m.%Y', '%d %b %Y', '%d-%b-%Y', '%d %B %Y'):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise UserError(_("Cannot read the date '%s'. Use the format YYYY-MM-DD.", s))


class LoanUploadWizard(models.TransientModel):
    _name = 'lds.loan.upload.wizard'
    _description = 'Upload Bank Loan Schedule'

    loan_id = fields.Many2one('lds.bank.loan', required=True, readonly=True)
    file = fields.Binary(string='Excel File (.xlsx)', required=True)
    filename = fields.Char()
    replace = fields.Boolean(string='Replace existing schedule', default=True)

    def action_download_template(self):
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Schedule'
        ws.append(['Date', 'Principal', 'Interest', 'Payment', 'Balance'])
        ws.append(['2026-12-01', 1000000, 150000, 1150000, 9000000])
        ws.append(['2027-01-01', 1000000, 135000, 1135000, 8000000])
        buf = io.BytesIO()
        wb.save(buf)
        att = self.env['ir.attachment'].create({
            'name': 'loan_schedule_template.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(buf.getvalue()),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        return {'type': 'ir.actions.act_url', 'url': '/web/content/%d?download=true' % att.id, 'target': 'self'}

    def action_import(self):
        self.ensure_one()
        try:
            import openpyxl
        except ImportError:
            raise UserError(_("Python package 'openpyxl' is not installed on the server (pip install openpyxl)."))
        loan = self.loan_id
        if loan.state == 'closed':
            raise UserError(_("Cannot change the schedule of a closed loan."))
        try:
            wb = openpyxl.load_workbook(io.BytesIO(base64.b64decode(self.file)), data_only=True)
        except Exception as e:
            raise UserError(_("Cannot read the file. Upload a valid .xlsx file.\n%s", e))
        rows = list(wb.active.iter_rows(values_only=True))

        # locate header row
        col = {}
        start = None
        for idx, row in enumerate(rows):
            found = {}
            for ci, cell in enumerate(row):
                for key, names in ALIASES.items():
                    if _norm(cell) in names and key not in found:
                        found[key] = ci
            if 'date' in found and ('principal' in found or 'payment' in found):
                col, start = found, idx + 1
                break
        if start is None:
            raise UserError(_("Header row not found. The first row must contain: Date, Principal, Interest, "
                              "(Payment), (Balance). Use 'Download Template'."))

        parsed = []
        for row in rows[start:]:
            if not row or row[col['date']] in (None, ''):
                continue
            interest = _to_float(row[col['interest']]) if 'interest' in col else 0.0
            if 'principal' in col:
                principal = _to_float(row[col['principal']])
            else:
                principal = _to_float(row[col['payment']]) - interest
            balance = _to_float(row[col['balance']]) if 'balance' in col else None
            parsed.append({'date': _to_date(row[col['date']]), 'principal': principal,
                           'interest': interest, 'balance': balance})
        if not parsed:
            raise UserError(_("No data rows found in the file."))
        parsed.sort(key=lambda r: r['date'])

        if self.replace:
            if loan.repayment_ids:
                raise UserError(_("This loan already has repayments. Untick 'Replace existing schedule' "
                                  "or delete the repayments first."))
            if loan.allocation_ids.filtered(lambda a: a.state != 'draft'):
                raise UserError(_("Some Discount Center interest was already accrued. "
                                  "Untick 'Replace existing schedule' to only add lines."))
            loan.allocation_ids.unlink()
            loan.line_ids.unlink()

        base = loan.principal or sum(r['principal'] for r in parsed)
        running = base - sum(loan.line_ids.mapped('principal'))
        start_no = len(loan.line_ids)
        vals = []
        for i, r in enumerate(parsed, start=1):
            running -= r['principal']
            vals.append((0, 0, {
                'number': start_no + i,
                'date': r['date'],
                'principal': r['principal'],
                'interest': r['interest'],
                'balance': r['balance'] if r['balance'] is not None else running,
            }))
        loan.write({'line_ids': vals})
        updates = {}
        if not loan.principal:
            updates['principal'] = base
        if not loan.duration:
            updates['duration'] = len(parsed)
        if updates:
            loan.write(updates)
        loan.distribution_ids.filtered(lambda d: d.state == 'confirmed')._generate_allocations()
        loan.message_post(body=_("%s schedule lines uploaded from Excel.", len(parsed)))
        return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {
            'title': _('Upload complete'), 'message': _('%s lines imported.', len(parsed)),
            'type': 'success', 'next': {'type': 'ir.actions.act_window_close'}}}
