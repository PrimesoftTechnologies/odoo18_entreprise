# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SaleBusinessModel(models.Model):
    _name = 'sale.business.model'
    _description = 'Business Model'
    _order = 'name'

    name = fields.Char(string='Business Name', required=True)
    code = fields.Char(string='Short Code', required=True)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True, default=lambda self: self.env.company,
        help="Only users working in this company see this Business Model.")
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'The Short Code must be unique.'),
    ]

    @api.constrains('code')
    def _check_code(self):
        for rec in self:
            if not rec.code or '/' in rec.code or ' ' in rec.code:
                raise ValidationError(_("The Short Code cannot contain spaces or '/'."))

    @api.depends('name', 'code')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = '%s (%s)' % (rec.name, rec.code) if rec.code else rec.name


class SaleOrderBusiness(models.Model):
    _inherit = 'sale.order'

    business_model_id = fields.Many2one(
        'sale.business.model', string='Business Model', required=True, tracking=True, ondelete='restrict', copy=True)

    @api.constrains('business_model_id', 'company_id')
    def _check_business_model_company(self):
        for order in self:
            model = order.business_model_id
            if model and model.company_id != order.company_id:
                raise ValidationError(_(
                    "The Business Model '%(model)s' belongs to %(company)s, not to the company of this order (%(order_company)s).",
                    model=model.name, company=model.company_id.name, order_company=order.company_id.name))

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        for order in orders:
            order._apply_business_prefix()
        return orders

    def write(self, vals):
        old_models = {}
        if 'business_model_id' in vals:
            old_models = {order.id: order.business_model_id for order in self}
        res = super().write(vals)
        if 'business_model_id' in vals:
            for order in self.filtered(lambda o: o.state in ('draft', 'sent')):
                order._apply_business_prefix(old_models.get(order.id))
        return res

    def _apply_business_prefix(self, old_model=None):
        """ S00013 -> HP/S00013 (Short Code of the chosen Business Model) """
        self.ensure_one()
        name = self.name or ''
        if not name or name == _("New"):
            return
        if old_model and old_model.code and name.startswith(old_model.code + '/'):
            name = name[len(old_model.code) + 1:]
        code = self.business_model_id.code
        if code and not name.startswith(code + '/'):
            name = '%s/%s' % (code, name)
        if name != self.name:
            self.name = name
