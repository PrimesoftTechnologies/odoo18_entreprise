from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestLocationOwnerValidation(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        group_ids = [
            cls.env.ref('base.group_user').id,
            cls.env.ref('stock.group_stock_user').id,
        ]
        Users = cls.env['res.users'].with_context(no_reset_password=True)

        def make_user(login):
            return Users.create({
                'name': login, 'login': login, 'email': '%s@example.com' % login,
                'groups_id': [(6, 0, group_ids)],
            })

        cls.src_owner = make_user('hill_src_owner')
        cls.dest_owner = make_user('hill_dest_owner')
        cls.other_user = make_user('hill_other_user')

        warehouse = cls.env['stock.warehouse'].search(
            [('company_id', '=', cls.env.company.id)], limit=1)
        parent = warehouse.lot_stock_id
        Location = cls.env['stock.location']
        cls.src_loc = Location.create({
            'name': 'Hill Src', 'usage': 'internal', 'location_id': parent.id,
            'location_owner_id': cls.src_owner.id})
        cls.dest_loc = Location.create({
            'name': 'Hill Dest', 'usage': 'internal', 'location_id': parent.id,
            'location_owner_id': cls.dest_owner.id})
        cls.free_loc = Location.create({
            'name': 'Hill Free', 'usage': 'internal', 'location_id': parent.id})
        cls.picking_type = warehouse.int_type_id
        cls.product = cls.env['product.product'].create({'name': 'Hill Product', 'type': 'consu'})

    def _make_picking(self, src, dest):
        return self.env['stock.picking'].create({
            'picking_type_id': self.picking_type.id,
            'location_id': src.id,
            'location_dest_id': dest.id,
            'move_ids': [(0, 0, {
                'name': self.product.name,
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'product_uom': self.product.uom_id.id,
                'location_id': src.id,
                'location_dest_id': dest.id,
            })],
        })

    def test_owners_follow_locations(self):
        picking = self._make_picking(self.src_loc, self.dest_loc)
        self.assertEqual(picking.location_owner_id, self.src_owner)
        self.assertEqual(picking.location_dest_owner_id, self.dest_owner)

    def test_source_owner_makes_it_pending(self):
        picking = self._make_picking(self.src_loc, self.dest_loc)
        picking.with_user(self.src_owner).button_validate()
        self.assertTrue(picking.pending_validation)
        self.assertEqual(picking.pending_validation_user_id, self.src_owner)

    def test_destination_owner_cannot_validate_first(self):
        picking = self._make_picking(self.src_loc, self.dest_loc)
        with self.assertRaises(UserError):
            picking.with_user(self.dest_owner).button_validate()

    def test_other_user_cannot_validate(self):
        picking = self._make_picking(self.src_loc, self.dest_loc)
        with self.assertRaises(UserError):
            picking.with_user(self.other_user).button_validate()

    def test_only_destination_owner_can_reject(self):
        picking = self._make_picking(self.src_loc, self.dest_loc)
        picking.with_user(self.src_owner).button_validate()
        with self.assertRaises(UserError):
            picking.with_user(self.other_user).action_reject_pending_validation()
        picking.with_user(self.dest_owner).action_reject_pending_validation()
        self.assertFalse(picking.pending_validation)

    def test_no_destination_owner_skips_flow(self):
        picking = self._make_picking(self.src_loc, self.free_loc)
        self.assertFalse(picking._requires_owner_validation())
