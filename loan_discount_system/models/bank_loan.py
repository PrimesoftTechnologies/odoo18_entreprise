# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountLoanDistributors(models.Model):
    _inherit = 'account.loan'

    lds_distributor_ids = fields.One2many(
        comodel_name='lds.customer.loan',
        compute='_compute_lds_distributors',
        string='Loan Distributors',
    )
    lds_distributor_count = fields.Integer(
        compute='_compute_lds_distributors',
        string='Distributors Count',
    )
    lds_total_distributed = fields.Float(
        compute='_compute_lds_distributors',
        string='Total Distributed',
    )

    @api.depends('name')
    def _compute_lds_distributors(self):
        Dist = self.env['lds.customer.loan'].sudo()
        for rec in self:
            dists = Dist.search([
                ('odoo_loan_model', '=', rec._name),
                ('odoo_loan_id', '=', rec.id),
            ])
            rec.lds_distributor_ids = dists
            rec.lds_distributor_count = len(dists)
            active_dists = dists.filtered(lambda d: d.state != 'draft')
            rec.lds_total_distributed = sum(active_dists.mapped('amount'))


class LdsBankLoanDynamicHook(models.AbstractModel):
    _name = 'lds.bank.loan.dynamic.hook'
    _description = 'Fallback Hook if Accounting > Loans uses a model other than account.loan'

    @api.model
    def _register_hook(self):
        res = super()._register_hook()
        self._ensure_other_loan_model()
        return res

    @api.model
    def _ensure_other_loan_model(self):
        model_name = self.env['lds.customer.loan']._default_loan_model()
        if not model_name or model_name == 'account.loan' or model_name not in self.env:
            return
        TargetModel = self.env[model_name]
        if 'lds_distributor_ids' not in TargetModel._fields:
            def _compute_dists(records):
                Dist = records.env['lds.customer.loan'].sudo()
                for rec in records:
                    dists = Dist.search([
                        ('odoo_loan_model', '=', rec._name),
                        ('odoo_loan_id', '=', rec.id),
                    ])
                    rec.lds_distributor_ids = dists
                    rec.lds_distributor_count = len(dists)
                    rec.lds_total_distributed = sum(dists.filtered(lambda d: d.state != 'draft').mapped('amount'))

            f_o2m = fields.One2many(comodel_name='lds.customer.loan', compute=_compute_dists, string='Loan Distributors')
            f_o2m.name = 'lds_distributor_ids'
            f_o2m.model_name = model_name
            TargetModel._fields['lds_distributor_ids'] = f_o2m

            f_cnt = fields.Integer(compute=_compute_dists, string='Distributors Count')
            f_cnt.name = 'lds_distributor_count'
            f_cnt.model_name = model_name
            TargetModel._fields['lds_distributor_count'] = f_cnt

            f_tot = fields.Float(compute=_compute_dists, string='Total Distributed')
            f_tot.name = 'lds_total_distributed'
            f_tot.model_name = model_name
            TargetModel._fields['lds_total_distributed'] = f_tot
