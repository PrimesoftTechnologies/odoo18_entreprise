from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AssetLocation(models.Model):
    _name = 'asset.location'
    _description = 'Asset Location'
    _parent_name = 'parent_id'
    _parent_store = True
    _rec_name = 'complete_name'
    _order = 'complete_name'

    name = fields.Char(required=True)
    complete_name = fields.Char(compute='_compute_complete_name', store=True, recursive=True)
    parent_id = fields.Many2one('asset.location', string='Parent Location', index=True,
                                ondelete='restrict')
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many('asset.location', 'parent_id', string='Sub-locations')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company)
    note = fields.Text()
    asset_count = fields.Integer(compute='_compute_asset_count')

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for rec in self:
            if rec.parent_id:
                rec.complete_name = '%s / %s' % (rec.parent_id.complete_name, rec.name)
            else:
                rec.complete_name = rec.name

    @api.constrains('parent_id')
    def _check_parent_id(self):
        if self._has_cycle():
            raise ValidationError(self.env._("You cannot create recursive locations."))

    def _compute_asset_count(self):
        data = self.env['asset.asset']._read_group(
            [('location_id', 'in', self.ids)], ['location_id'], ['__count'])
        mapped = {loc.id: count for loc, count in data}
        for rec in self:
            rec.asset_count = mapped.get(rec.id, 0)

    def action_view_assets(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.complete_name,
            'res_model': 'asset.asset',
            'view_mode': 'list,kanban,form',
            'domain': [('location_id', 'child_of', self.id)],
            'context': {'default_location_id': self.id},
        }
