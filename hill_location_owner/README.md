# hill_location_owner (Odoo 18)

Depends on: `stock`, `mail`.

## 1. Assign owners (one or many)
Inventory > Configuration > Locations > open a location > **Location Owners** (pick as many internal users as you need).
Editing locations is limited by Odoo's standard rights (Inventory Manager).

## 2. Owner approval: Internal Transfers AND Receipts
Applies to transfers whose **picking type is Internal or Receipt** and whose **destination location has at least one owner**.
Deliveries and other types keep the standard Odoo flow.

1. A source owner presses **Validate** -> transfer becomes **Pending Validation**
   (every destination owner gets a message + a to-do activity).
   * Internal transfer: ANY source owner starts it.
   * Receipt: the vendor location normally has no owner, so ANY user who is not a
     destination owner starts it (e.g. purchasing / the person who checked the goods).
2. ANY destination owner can **Validate** (= receive; the normal Odoo flow continues)
   or **Reject Validation**. When validated, the to-dos of all destination owners are closed.
3. Until step 1, destination owners see no action buttons; other users cannot validate at step 2.
4. A user who owns both the source and the destination validates directly.
5. If the source has owners, only they can start step 1.
6. If the destination has no owner, the standard Odoo flow is used.

"Mark as Todo" is also restricted server-side (sudo / cron / return wizard are not affected).

To change which types are covered, edit `OWNER_VALIDATION_TYPES` in `models/stock_picking.py`.

## Upgrade notes
* 18.0.1.1.0 replaced the single field `location_owner_id` by the many2many `location_owner_ids`;
  re-enter owners if an older build was installed.
* 18.0.1.2.0 added Receipts (no data change).

## Tests
`odoo -d <db> -i hill_location_owner --test-tags /hill_location_owner --stop-after-init`
