# -*- coding: utf-8 -*-
from odoo import api, fields, models


class LdsBankLoanHook(models.AbstractModel):
    _name = 'lds.bank.loan.hook'
    _description = 'Dynamic Hook for Bank Loan Form (Loan Distributors Tab)'

    @api.model
    def _register_hook(self):
        res = super()._register_hook()
        self._install_bank_loan_extension()
        return res

    @api.model
    def _attach_field(self, target_model, field_name, field_obj):
        """Attach a field cleanly to target_model and Odoo registry."""
        field_obj.name = field_name
        field_obj.model_name = target_model._name
        target_model._fields[field_name] = field_obj
        setattr(target_model.__class__, field_name, field_obj)
        if hasattr(target_model, '_field_create'):
            try:
                target_model._field_create(field_obj)
            except Exception:
                pass

    @api.model
    def _install_bank_loan_extension(self):
        LoanModel = self.env['lds.customer.loan']
        model_name = LoanModel._default_loan_model() or ('account.loan' if 'account.loan' in self.env else False)
        if not model_name or model_name not in self.env:
            return

        TargetModel = self.env[model_name]

        def _compute_lds_distributors(records):
            Dist = records.env['lds.customer.loan']
            for rec in records:
                dists = Dist.search([
                    ('odoo_loan_model', '=', rec._name),
                    ('odoo_loan_id', '=', rec.id),
                ])
                rec.lds_distributor_ids = dists
                active_dists = dists.filtered(lambda d: d.state != 'draft')
                rec.lds_total_distributed = sum(active_dists.mapped('amount'))
                rec.lds_distributor_count = len(dists)

        changed = False
        if 'lds_distributor_ids' not in TargetModel._fields:
            self._attach_field(
                TargetModel,
                'lds_distributor_ids',
                fields.One2many(
                    comodel_name='lds.customer.loan',
                    compute=_compute_lds_distributors,
                    string='Loan Distributors',
                    store=False,
                ),
            )
            changed = True

        if 'lds_total_distributed' not in TargetModel._fields:
            self._attach_field(
                TargetModel,
                'lds_total_distributed',
                fields.Float(
                    compute=_compute_lds_distributors,
                    string='Total Distributed',
                    store=False,
                ),
            )
            changed = True

        if 'lds_distributor_count' not in TargetModel._fields:
            self._attach_field(
                TargetModel,
                'lds_distributor_count',
                fields.Integer(
                    compute=_compute_lds_distributors,
                    string='Distributors Count',
                    store=False,
                ),
            )
            changed = True

        if changed and hasattr(self.env.registry, 'setup_models'):
            try:
                self.env.registry.setup_models(self.env.cr)
            except Exception:
                pass

        View = self.env['ir.ui.view'].sudo()
        Data = self.env['ir.model.data'].sudo()
        xmlid_rec = Data.search([
            ('module', '=', 'loan_discount_system'),
            ('name', '=', 'view_bank_loan_form_lds_distributors'),
        ], limit=1)

        form_views = View.search([
            ('model', '=', model_name),
            ('type', '=', 'form'),
            ('inherit_id', '=', False),
        ], order='priority asc, id asc')

        target_view = False
        for v in form_views:
            if 'Loan Settings' in (v.arch_db or '') or 'notebook' in (v.arch_db or ''):
                target_view = v
                break
        if not target_view and form_views:
            target_view = form_views[0]

        if not target_view:
            return

        arch_str = target_view.arch_db or ''
        if "Loan Settings" in arch_str:
            xpath_expr = "//notebook/page[@string='Loan Settings']"
            xpath_pos = "after"
        else:
            xpath_expr = "//notebook"
            xpath_pos = "inside"

        arch = f"""<?xml version="1.0"?>
<xpath expr="{xpath_expr}" position="{xpath_pos}">
    <page string="Loan Distributors" name="lds_loan_distributors">
        <group>
            <group>
                <field name="lds_distributor_count" readonly="1"/>
            </group>
            <group>
                <field name="lds_total_distributed" readonly="1"/>
            </group>
        </group>
        <field name="lds_distributor_ids" readonly="1" nolabel="1">
            <list decoration-success="state == 'closed'" decoration-info="state == 'draft'">
                <field name="name"/>
                <field name="partner_id" string="Distributor (Customer)"/>
                <field name="date"/>
                <field name="duration"/>
                <field name="amount" sum="Total Amount"/>
                <field name="interest" sum="Total Interest"/>
                <field name="outstanding_balance" sum="Total Outstanding"/>
                <field name="currency_id" column_invisible="1"/>
                <field name="state" widget="badge"/>
                <button name="action_open_distribution" type="object" string="Open" icon="fa-external-link"/>
            </list>
        </field>
    </page>
</xpath>"""

        if xmlid_rec:
            existing_view = View.browse(xmlid_rec.res_id).exists()
            if existing_view:
                existing_view.write({
                    'model': model_name,
                    'inherit_id': target_view.id,
                    'arch': arch,
                })
                return

        new_view = View.create({
            'name': f'{model_name}.form.lds.distributors',
            'model': model_name,
            'inherit_id': target_view.id,
            'arch': arch,
        })
        Data.create({
            'module': 'loan_discount_system',
            'name': 'view_bank_loan_form_lds_distributors',
            'model': 'ir.ui.view',
            'res_id': new_view.id,
            'noupdate': False,
        })
