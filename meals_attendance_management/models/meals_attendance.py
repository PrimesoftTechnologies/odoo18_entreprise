from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class MealsAttendance(models.Model):
    """One sheet = customer + meal type + date. Lines = employees (ticked when they ate)."""
    _name = 'meals.attendance'
    _description = 'Meals Attendance Sheet'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(default=lambda s: _('New'), readonly=True, copy=False)
    customer_id = fields.Many2one(
        'res.partner', string='Customer', required=True, index=True, tracking=True,
        domain=[('is_meal_customer', '=', True)])
    meal_type_id = fields.Many2one(
        'meals.type', string='Meal Type', required=True, index=True, tracking=True,
        domain="[('customer_id', '=', customer_id)]")
    date = fields.Date(required=True, default=fields.Date.context_today, index=True, tracking=True)
    department_id = fields.Many2one(
        'hr.department', string='Load Department Only', copy=False,
        domain="[('meal_customer_id', '=', customer_id)]",
        help="Optional: when loading employees, only load this department.")
    state = fields.Selection(
        [('draft', 'Draft'), ('confirmed', 'Confirmed')],
        default='draft', required=True, tracking=True, copy=False)
    line_ids = fields.One2many('meals.attendance.line', 'attendance_id', string='Employees', copy=False)
    total_count = fields.Integer(compute='_compute_totals', store=True)
    attended_count = fields.Integer(string='Attended', compute='_compute_totals', store=True)
    amount_total = fields.Monetary(compute='_compute_totals', store=True, currency_field='currency_id')
    invoiced = fields.Boolean(compute='_compute_invoiced')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company, required=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    user_id = fields.Many2one('res.users', string='Recorded By', default=lambda s: s.env.user, readonly=True)
    note = fields.Text()

    _sql_constraints = [
        ('sheet_uniq', 'unique(customer_id, meal_type_id, date)',
         'An attendance sheet already exists for this customer, meal type and date.'),
    ]

    # ---------------- computes / constraints ----------------
    @api.depends('line_ids.attended', 'line_ids.amount')
    def _compute_totals(self):
        for rec in self:
            rec.total_count = len(rec.line_ids)
            rec.attended_count = len(rec.line_ids.filtered('attended'))
            rec.amount_total = sum(rec.line_ids.mapped('amount'))

    @api.depends('line_ids.invoice_id')
    def _compute_invoiced(self):
        for rec in self:
            rec.invoiced = bool(rec.line_ids.filtered('invoice_id'))

    @api.constrains('customer_id', 'meal_type_id')
    def _check_meal_type_customer(self):
        for rec in self:
            if rec.meal_type_id.customer_id != rec.customer_id:
                raise ValidationError(_("The meal type does not belong to the selected customer."))

    @api.onchange('customer_id')
    def _onchange_customer_id(self):
        self.meal_type_id = False
        self.department_id = False
        self.line_ids = [Command.clear()]

    # ---------------- ORM ----------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('meals.attendance') or _('New')
        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        if 'meal_type_id' in vals:
            for rec in self.filtered(lambda r: r.state == 'draft'):
                rec.line_ids.write({'unit_price': rec.meal_type_id.price})
        return res

    @api.ondelete(at_uninstall=False)
    def _unlink_except_confirmed(self):
        for rec in self:
            if rec.state != 'draft' or rec.invoiced:
                raise UserError(_("Only draft, non-invoiced sheets can be deleted."))

    # ---------------- actions ----------------
    def action_load_employees(self):
        Employee = self.env['hr.employee']
        Line = self.env['meals.attendance.line']
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_("You can only load employees on a draft sheet."))
            domain = [('meal_customer_id', '=', rec.customer_id.id), ('is_meal_employee', '=', True)]
            if rec.department_id:
                domain.append(('department_id', '=', rec.department_id.id))
            employees = Employee.search(domain, order='department_id, name') - rec.line_ids.employee_id
            Line.create([{'attendance_id': rec.id, 'employee_id': e.id} for e in employees])
        return True

    def action_select_all(self):
        for rec in self.filtered(lambda r: r.state == 'draft'):
            rec.line_ids.write({'attended': True})

    def action_unselect_all(self):
        for rec in self.filtered(lambda r: r.state == 'draft'):
            rec.line_ids.write({'attended': False})

    def action_confirm(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError(_("Load the employees first."))
            if not rec.attended_count:
                raise UserError(_("Nobody is ticked as attended on %s.", rec.name))
            rec.state = 'confirmed'

    def action_draft(self):
        for rec in self:
            if rec.invoiced:
                raise UserError(_("%s is already invoiced and cannot be reset.", rec.name))
            rec.state = 'draft'


class MealsAttendanceLine(models.Model):
    _name = 'meals.attendance.line'
    _description = 'Meals Attendance Line'
    _order = 'date desc, department_id, employee_id, id'

    attendance_id = fields.Many2one('meals.attendance', required=True, ondelete='cascade', index=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, index=True,
                                  ondelete='restrict')
    employee_no = fields.Char(related='employee_id.meal_employee_no', string='Employee No.')
    department_id = fields.Many2one('hr.department', string='Department', index=True)  # snapshot
    attended = fields.Boolean(default=False)
    remark = fields.Char()
    scan_time = fields.Float(string='Scan Time', help="Time of the machine scan.")
    source = fields.Selection([('manual', 'Manual'), ('machine', 'Machine')], default='manual', required=True)
    qty = fields.Integer(compute='_compute_amount', store=True)
    unit_price = fields.Monetary(currency_field='currency_id')
    amount = fields.Monetary(compute='_compute_amount', store=True, currency_field='currency_id')
    invoice_id = fields.Many2one('account.move', string='Invoice', readonly=True, copy=False,
                                 index=True, ondelete='set null')
    # stored related fields -> fast reporting
    customer_id = fields.Many2one(related='attendance_id.customer_id', store=True, index=True)
    meal_type_id = fields.Many2one(related='attendance_id.meal_type_id', store=True, index=True)
    date = fields.Date(related='attendance_id.date', store=True, index=True)
    state = fields.Selection(related='attendance_id.state', store=True)
    company_id = fields.Many2one(related='attendance_id.company_id', store=True)
    currency_id = fields.Many2one(related='attendance_id.currency_id')

    _sql_constraints = [
        ('employee_sheet_uniq', 'unique(attendance_id, employee_id)',
         'An employee can appear only once per sheet.'),
    ]

    @api.depends('attended', 'unit_price')
    def _compute_amount(self):
        for line in self:
            line.qty = 1 if line.attended else 0
            line.amount = line.unit_price if line.attended else 0.0

    @api.constrains('employee_id', 'attendance_id')
    def _check_employee_customer(self):
        for line in self:
            if line.employee_id.meal_customer_id != line.attendance_id.customer_id:
                raise ValidationError(_(
                    "Employee %s does not belong to the customer of this sheet.",
                    line.employee_id.name))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('attendance_id'):
                sheet = self.env['meals.attendance'].browse(vals['attendance_id'])
                vals.setdefault('unit_price', sheet.meal_type_id.price)
            if vals.get('employee_id') and not vals.get('department_id'):
                vals['department_id'] = self.env['hr.employee'].browse(vals['employee_id']).department_id.id
        return super().create(vals_list)

    def write(self, vals):
        if {'attended', 'employee_id', 'unit_price', 'attendance_id'} & set(vals) \
                and self.filtered('invoice_id'):
            raise UserError(_("Invoiced attendance lines cannot be modified."))
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_locked(self):
        if self.filtered(lambda l: l.invoice_id or l.state == 'confirmed'):
            raise UserError(_("Confirmed or invoiced lines cannot be deleted."))
