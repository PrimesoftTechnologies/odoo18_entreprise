from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestLocationOwnersValidation(TransactionCase):

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

        cls.src_a = make_user('hill_src_a')
        cls.src_b = make_user('hill_src_b')
        cls.dest_a = make_user('hill_dest_a')
        cls.dest_b = make_user('hill_dest_b')
        cls.other_user = make_user('hill_other_user')

        warehouse = cls.env['stock.warehouse'].search(
            [('company_id', '=', cls.env.company.id)], limit=1)
        parent = warehouse.lot_stock_id
        Location = cls.env['stock.location']
        cls.src_loc = Location.create({
            'name': 'Hill Src', 'usage': 'internal', 'location_id': parent.id,
            'location_owner_ids': [(6, 0, (cls.src_a | cls.src_b).ids)]})
        cls.dest_loc = Location.create({
            'name': 'Hill Dest', 'usage': 'internal', 'location_id': parent.id,
            'location_owner_ids': [(6, 0, (cls.dest_a | cls.dest_b).ids)]})
        cls.free_loc = Location.create({
            'name': 'Hill Free', 'usage': 'internal', 'location_id': parent.id})
        # production locations: one with owners (approvers of pick components), one without
        cls.production_loc = Location.create({
            'name': 'Hill Production', 'usage': 'production',
            'location_owner_ids': [(6, 0, (cls.dest_a | cls.dest_b).ids)]})
        cls.free_production_loc = Location.create({
            'name': 'Hill Production Free', 'usage': 'production'})
        cls.supplier_loc = cls.env.ref('stock.stock_location_suppliers')
        cls.customer_loc = cls.env.ref('stock.stock_location_customers')
        cls.internal_type = warehouse.int_type_id
        cls.receipt_type = warehouse.in_type_id
        cls.delivery_type = warehouse.out_type_id
        cls.product = cls.env['product.product'].create({'name': 'Hill Product', 'type': 'consu'})

    def _make_picking(self, src, dest, picking_type=None):
        return self.env['stock.picking'].create({
            'picking_type_id': (picking_type or self.internal_type).id,
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

    # ------------------------------------------------------------ internal transfers
    def test_owners_follow_locations(self):
        picking = self._make_picking(self.src_loc, self.dest_loc)
        self.assertEqual(picking.location_owner_ids, self.src_a | self.src_b)
        self.assertEqual(picking.location_dest_owner_ids, self.dest_a | self.dest_b)

    def test_any_source_owner_makes_it_pending(self):
        for owner in (self.src_a, self.src_b):
            picking = self._make_picking(self.src_loc, self.dest_loc)
            picking.with_user(owner).button_validate()
            self.assertTrue(picking.pending_validation)
            self.assertEqual(picking.pending_validation_user_id, owner)

    def test_every_destination_owner_gets_an_activity(self):
        picking = self._make_picking(self.src_loc, self.dest_loc)
        picking.with_user(self.src_a).button_validate()
        assigned = picking.activity_ids.mapped('user_id')
        self.assertEqual(assigned, self.dest_a | self.dest_b)

    def test_destination_owners_cannot_validate_first(self):
        picking = self._make_picking(self.src_loc, self.dest_loc)
        for owner in (self.dest_a, self.dest_b):
            with self.assertRaises(UserError):
                picking.with_user(owner).button_validate()

    def test_other_user_cannot_validate(self):
        picking = self._make_picking(self.src_loc, self.dest_loc)
        with self.assertRaises(UserError):
            picking.with_user(self.other_user).button_validate()

    def test_pending_blocks_source_owner_and_others(self):
        picking = self._make_picking(self.src_loc, self.dest_loc)
        picking.with_user(self.src_a).button_validate()
        for user in (self.src_b, self.other_user):
            with self.assertRaises(UserError):
                picking.with_user(user).button_validate()

    def test_any_destination_owner_can_reject(self):
        picking = self._make_picking(self.src_loc, self.dest_loc)
        picking.with_user(self.src_a).button_validate()
        with self.assertRaises(UserError):
            picking.with_user(self.other_user).action_reject_pending_validation()
        picking.with_user(self.dest_b).action_reject_pending_validation()
        self.assertFalse(picking.pending_validation)

    def test_button_flags_per_user(self):
        picking = self._make_picking(self.src_loc, self.dest_loc)
        self.assertFalse(picking.with_user(self.src_b).hide_validation_buttons)
        self.assertTrue(picking.with_user(self.dest_a).hide_validation_buttons)
        self.assertTrue(picking.with_user(self.other_user).hide_validation_buttons)
        picking.with_user(self.src_a).button_validate()
        self.assertFalse(picking.with_user(self.dest_b).hide_validation_buttons)
        self.assertTrue(picking.with_user(self.src_b).hide_validation_buttons)

    def test_no_destination_owner_skips_flow(self):
        picking = self._make_picking(self.src_loc, self.free_loc)
        self.assertFalse(picking._requires_owner_validation())

    # ------------------------------------------------------------ receipts
    def test_receipt_requires_owner_validation(self):
        picking = self._make_picking(self.supplier_loc, self.dest_loc, self.receipt_type)
        self.assertTrue(picking._requires_owner_validation())

    def test_receipt_destination_owner_cannot_validate_first(self):
        picking = self._make_picking(self.supplier_loc, self.dest_loc, self.receipt_type)
        for owner in (self.dest_a, self.dest_b):
            with self.assertRaises(UserError):
                picking.with_user(owner).button_validate()

    def test_receipt_non_owner_starts_then_destination_owner_can_reject(self):
        # vendor location has no owner -> anyone except the destination owners starts it
        picking = self._make_picking(self.supplier_loc, self.dest_loc, self.receipt_type)
        picking.with_user(self.other_user).button_validate()
        self.assertTrue(picking.pending_validation)
        self.assertEqual(picking.activity_ids.mapped('user_id'), self.dest_a | self.dest_b)
        with self.assertRaises(UserError):
            picking.with_user(self.other_user).action_reject_pending_validation()
        picking.with_user(self.dest_a).action_reject_pending_validation()
        self.assertFalse(picking.pending_validation)

    def test_receipt_button_flags(self):
        picking = self._make_picking(self.supplier_loc, self.dest_loc, self.receipt_type)
        self.assertTrue(picking.with_user(self.dest_a).hide_validation_buttons)
        self.assertFalse(picking.with_user(self.other_user).hide_validation_buttons)
        picking.with_user(self.other_user).button_validate()
        self.assertFalse(picking.with_user(self.dest_a).hide_validation_buttons)
        self.assertTrue(picking.with_user(self.other_user).hide_validation_buttons)

    def test_receipt_without_destination_owner_skips_flow(self):
        picking = self._make_picking(self.supplier_loc, self.free_loc, self.receipt_type)
        self.assertFalse(picking._requires_owner_validation())

    # ------------------------------------------------------------ deliveries
    # approvers = SOURCE owners (they hand the goods over); customer has no owner,
    # so any user who is not a source owner starts it.
    def test_delivery_requires_validation_from_source_owners(self):
        picking = self._make_picking(self.src_loc, self.customer_loc, self.delivery_type)
        self.assertTrue(picking._requires_owner_validation())
        starters, approvers = picking._get_owner_roles()
        self.assertFalse(starters)
        self.assertEqual(approvers, self.src_a | self.src_b)

    def test_delivery_source_owner_cannot_validate_first(self):
        picking = self._make_picking(self.src_loc, self.customer_loc, self.delivery_type)
        for owner in (self.src_a, self.src_b):
            with self.assertRaises(UserError):
                picking.with_user(owner).button_validate()

    def test_delivery_non_owner_starts_then_source_owner_can_reject(self):
        picking = self._make_picking(self.src_loc, self.customer_loc, self.delivery_type)
        picking.with_user(self.other_user).button_validate()
        self.assertTrue(picking.pending_validation)
        self.assertEqual(picking.activity_ids.mapped('user_id'), self.src_a | self.src_b)
        with self.assertRaises(UserError):
            picking.with_user(self.other_user).action_reject_pending_validation()
        picking.with_user(self.src_b).action_reject_pending_validation()
        self.assertFalse(picking.pending_validation)

    def test_delivery_button_flags(self):
        picking = self._make_picking(self.src_loc, self.customer_loc, self.delivery_type)
        self.assertTrue(picking.with_user(self.src_a).hide_validation_buttons)
        self.assertFalse(picking.with_user(self.other_user).hide_validation_buttons)
        picking.with_user(self.other_user).button_validate()
        self.assertFalse(picking.with_user(self.src_a).hide_validation_buttons)
        self.assertTrue(picking.with_user(self.other_user).hide_validation_buttons)

    def test_delivery_from_location_without_owner_skips_flow(self):
        picking = self._make_picking(self.free_loc, self.customer_loc, self.delivery_type)
        self.assertFalse(picking._requires_owner_validation())

    # ------------------------------------------------------------ pick components
    # internal move stock -> production location: same rules as an internal transfer
    # (approvers = destination (production) owners, starters = source owners)
    def test_pick_components_approvers_are_production_owners(self):
        picking = self._make_picking(self.src_loc, self.production_loc, self.internal_type)
        self.assertTrue(picking._requires_owner_validation())
        starters, approvers = picking._get_owner_roles()
        self.assertEqual(starters, self.src_a | self.src_b)
        self.assertEqual(approvers, self.dest_a | self.dest_b)

    def test_pick_components_flow(self):
        picking = self._make_picking(self.src_loc, self.production_loc, self.internal_type)
        for owner in (self.dest_a, self.dest_b, self.other_user):
            with self.assertRaises(UserError):
                picking.with_user(owner).button_validate()
        picking.with_user(self.src_a).button_validate()
        self.assertTrue(picking.pending_validation)
        self.assertEqual(picking.activity_ids.mapped('user_id'), self.dest_a | self.dest_b)
        with self.assertRaises(UserError):
            picking.with_user(self.src_b).action_reject_pending_validation()
        picking.with_user(self.dest_b).action_reject_pending_validation()
        self.assertFalse(picking.pending_validation)

    def test_pick_components_without_production_owner_skips_flow(self):
        # source owners alone do not trigger approval any more
        picking = self._make_picking(self.src_loc, self.free_production_loc, self.internal_type)
        self.assertFalse(picking._requires_owner_validation())

    # ------------------------------------------------------------ mark as todo guard
    def test_mark_as_todo_guard_only_with_button_context(self):
        picking = self._make_picking(self.src_loc, self.dest_loc)
        picking.with_user(self.dest_a).action_confirm()  # automatic flows are not blocked
        picking2 = self._make_picking(self.src_loc, self.dest_loc)
        with self.assertRaises(UserError):
            picking2.with_user(self.dest_a).with_context(hill_owner_check=True).action_confirm()
