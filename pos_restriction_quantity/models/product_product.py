from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    pos_qty_available = fields.Float(
        string='POS On Hand Quantity',
        compute='_compute_pos_qty_available',
        digits='Product Unit of Measure',
    )

    def _compute_pos_qty_available(self):
        for product in self:
            product.pos_qty_available = product.qty_available

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields_list = super()._load_pos_data_fields(config_id)
        for name in ('pos_qty_available', 'is_storable'):
            if name not in fields_list:
                fields_list.append(name)
        return fields_list

    @api.model
    def _get_pos_location(self, config):
        return config.picking_type_id.default_location_src_id

    @api.model
    def _load_pos_data(self, data):
        res = super()._load_pos_data(data)
        config = self.env['pos.config'].browse(data['pos.config']['data'][0]['id'])
        location = self._get_pos_location(config)
        if location and res.get('data'):
            ids = [rec['id'] for rec in res['data']]
            products = self.sudo().browse(ids).with_context(location=location.id)
            qty_map = {p.id: p.qty_available for p in products}
            for rec in res['data']:
                rec['pos_qty_available'] = qty_map.get(rec['id'], 0.0)
        return res

    @api.model
    def get_pos_stock_qty(self, config_id, product_ids):
        """Return {product_id: on_hand_qty} for the POS source location."""
        config = self.env['pos.config'].browse(config_id)
        location = self._get_pos_location(config)
        if not location:
            return {}
        products = self.sudo().browse(product_ids).with_context(location=location.id)
        return {p.id: p.qty_available for p in products}
