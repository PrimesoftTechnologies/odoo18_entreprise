# hill_location_owner (Odoo 18)

Depends on: `stock`, `mail`.

## 1. Assign owners
Inventory > Configuration > Locations > open a location > **Location Owner** (internal user).
Editing locations is limited by Odoo's standard rights (Inventory Manager).

## 2. Internal transfer approval
Applies only to transfers whose **picking type is Internal** and whose **destination location has an owner**.

1. Source owner presses **Validate** -> transfer becomes **Pending Validation**
   (destination owner gets a message + activity).
2. Destination owner can **Validate** (normal Odoo flow continues) or **Reject Validation**.
3. Until step 1, the destination owner sees no action buttons; other users cannot validate.
4. If one person owns both locations, Validate works directly.
5. If the source has no owner, anyone except the destination owner may start step 1.
6. If the destination has no owner, the standard Odoo flow is used.

"Mark as Todo" is also restricted server-side (sudo / cron are not affected).

## Tests
`odoo -d <db> -i hill_location_owner --test-tags /hill_location_owner --stop-after-init`
