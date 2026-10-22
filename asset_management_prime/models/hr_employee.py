from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    asset_count = fields.Integer('Assets Held', compute='_compute_asset_count')

    def _compute_asset_count(self):
        data = self.env['asset.asset']._read_group(
            [('employee_id', 'in', self.ids)], ['employee_id'], ['__count'])
        mapped = {emp.id: count for emp, count in data}
        for emp in self:
            emp.asset_count = mapped.get(emp.id, 0)

    def action_view_assets(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("Assets of %s", self.name),
            'res_model': 'asset.asset',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
        }
