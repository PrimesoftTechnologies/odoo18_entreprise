from odoo import api, fields, models

from .view_utils import inject_location_form, inject_location_list


class StockLocation(models.Model):
    _inherit = 'stock.location'

    location_owner_ids = fields.Many2many(
        'res.users', 'stock_location_owner_rel', 'location_id', 'user_id',
        string='Location Owners',
        domain=[('share', '=', False)],
        help='Users responsible for this location. On internal transfers, any owner of the '
             'destination location can validate (or reject) the transfer.')

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == 'form':
            inject_location_form(arch)
        elif view_type in ('list', 'tree'):
            inject_location_list(arch)
        return arch, view
