from odoo import api, fields, models

from .view_utils import inject_location_form, inject_location_list


class StockLocation(models.Model):
    _inherit = 'stock.location'

    location_owner_id = fields.Many2one(
        'res.users', string='Location Owner', index=True,
        domain=[('share', '=', False)],
        help='User responsible for this location. For internal transfers, the owner of the '
             'destination location must validate the transfer.')

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == 'form':
            inject_location_form(arch)
        elif view_type in ('list', 'tree'):
            inject_location_list(arch)
        return arch, view
