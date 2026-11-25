# hill_location_owner (Odoo 18)

Depends on: `stock`, `mail`.

## 1. Assign owners (one or many)
Inventory > Configuration > Locations > open a location > **Location Owners** (pick as many internal users as you need).
Editing locations is limited by Odoo's standard rights (Inventory Manager).

## 2. Owner approval
Covers **Internal Transfers, Receipts, Deliveries and Pick Components**.
Each transfer has two roles:

* **Approvers** - owners who give the FINAL validation (they receive / hand over the goods).
* **Starters** - owners of the other side who make the transfer "Pending". If that side has no owner,
  ANY user who is not an approver can start it.

| Type | Approvers | Starters |
|---|---|---|
| Internal Transfer | destination owners | source owners (or anyone else if none) |
| Receipt | destination owners | source owners (vendor: none -> anyone not an approver) |
| Pick Components (stock -> Production location) | **destination (Production) owners** | source owners (or anyone else if none) |
| Delivery | **source owners** | destination owners (customer: none -> anyone not an approver) |

Flow:
1. A starter presses **Validate** -> transfer becomes **Pending Validation**
   (every approver gets a message + a to-do activity).
2. ANY approver can **Validate** (normal Odoo flow continues) or **Reject Validation**.
   When validated, the to-dos of all approvers are closed.
3. Until step 1, approvers see no action buttons. At step 2 nobody else can validate.
4. A user who is both starter and approver validates directly.
5. If the approving side has no owner at all, the standard Odoo flow is used.

### Pick Components
Pick Components are ordinary *internal* transfers from stock to the production location, so they follow the
Internal Transfer rules: the **Production location must have owners** (Inventory > Configuration > Locations >
Virtual Locations/Production), otherwise approval is skipped. Note that this location is shared by all
manufacturing orders of the company, so its owners approve every Pick Components transfer.
Owners of the source (e.g. Store A) are the *starters*; if the source has no owner, any non-approver can start.

"Mark as Todo": the button is hidden for users who may not act, and the button call is also
checked server-side. Automatic flows (sale, purchase, POS, MRP, returns) never send the flag, so they are not blocked.
Validate is always enforced server-side.

Pick / Pack steps of multi-step deliveries are ordinary internal transfers (approvers = destination owners).
To change which picking types are covered, edit `OWNER_VALIDATION_TYPES` in `models/stock_picking.py`.

## Approval bell
Every approver gets a bell + a sticky "Approval needed" notification (with an *Open* button):
* right after login (web client load), if transfers are waiting for his approval;
* live, when a new approval request arrives while he is logged in.

Clicking **Open** closes the notification, opens the transfer and removes the approver's OWN to-do activity
for it (the transfer stays pending; other approvers keep theirs). Because that to-do is gone, the bell will
not remind him again at the next login - the transfer is still listed as pending on the transfers list.

Sound: one soft bell, `static/src/sounds/approval_bell.wav` (replace the file to change the tone).
Loudness: `BELL_VOLUME` (0 to 1) at the top of `static/src/js/approval_bell.js`.
Browsers may block sound until the user has interacted with the page; in that case the bell rings on the
first click / key press / tap, and the notification is always shown. A muted tab or device stays silent.

## Upgrade notes
* 18.0.1.1.0: single field `location_owner_id` replaced by many2many `location_owner_ids`.
* 18.0.1.2.0: Receipts added.
* 18.0.1.3.0: Deliveries and Pick Components added. Helper fields renamed (`is_approver`, `hide_approver_buttons`).
* 18.0.1.5.1: softer single bell; Open removes the approver's own activity.
* 18.0.1.5.0: approval bell (login + live). Clear the browser cache / reload after upgrading.
* 18.0.1.4.0: Pick Components are now approved by destination (Production) owners instead of source owners.
  Set owners on the Production location after upgrading. No stored data changes.

## Tests
`odoo -d <db> -i hill_location_owner --test-tags /hill_location_owner --stop-after-init`
