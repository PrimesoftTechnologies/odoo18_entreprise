# hill_location_owner (Odoo 18)

Depends on: `stock`, `mail`.

## 1. Assign owners (one or many)
Inventory > Configuration > Locations > open a location > **Location Owners** (pick as many internal users as you need).
Editing locations is limited by Odoo's standard rights (Inventory Manager).

## 2. Internal transfer approval
Applies only to transfers whose **picking type is Internal** and whose **destination location has at least one owner**.

1. ANY source owner presses **Validate** -> transfer becomes **Pending Validation**
   (every destination owner gets a message + a to-do activity).
2. ANY destination owner can **Validate** (normal Odoo flow continues) or **Reject Validation**.
   When it is validated, the to-dos of all destination owners are closed.
3. Until step 1, destination owners see no action buttons; other users cannot validate.
4. A user who is owner of both the source and the destination validates directly.
5. If the source has no owner, anyone except the destination owners may start step 1.
6. If the destination has no owner, the standard Odoo flow is used.

"Mark as Todo" is also restricted server-side (sudo / cron are not affected).

## Upgrade note
Version 18.0.1.1.0 replaced the single field `location_owner_id` by the many2many `location_owner_ids`.
If an older build was already installed, re-enter the owners (or migrate the data) after upgrading.

## Tests
`odoo -d <db> -i hill_location_owner --test-tags /hill_location_owner --stop-after-init`
