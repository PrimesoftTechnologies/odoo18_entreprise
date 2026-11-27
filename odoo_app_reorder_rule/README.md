# odoo_app_reorder_rule (Odoo 18)

Alerts when On Hand < Minimum of a Reorder Rule.

## Install
1. Copy the folder `odoo_app_reorder_rule` into your custom addons path.
2. Restart Odoo, enable Developer Mode, Apps > Update Apps List.
3. Search "Reorder Rule Alerts" and Install.

## Test
1. Inventory > Operations > Replenishment: create a rule for a product, Min = 7.
2. Make On Hand 10 (Inventory Adjustment), then reduce to 6 (validate).
3. Pop-up + bell counter + tab badge + browser notification + inbox/email appear.
4. All alerts: Inventory > Reorder Alerts.

## Who receives alerts
Users in group "Reorder Alert Receiver" (Inventory Managers by default).
Add more in Settings > Users > (user) > Reorder Alert Receiver.

## Notes
* Browser notifications need HTTPS and you must click "Allow".
* Alerts are re-checked every 15 min by cron as a safety net.
* One alert per rule; it is closed automatically when stock is back >= Minimum.

## App icon badge (v1.1)
The module appends a `push` handler to Odoo's service worker
(`/web/service-worker.js`). On every push it calls
`/reorder_alert/badge_count` and sets the icon badge to the number of open alerts.
After upgrading: open the installed app once (or remove and re-install it) so the
phone downloads the new service worker. Check it at
https://YOUR-DOMAIN/web/service-worker.js (search for "reorder_alert/badge_count").
Android launchers may show a dot instead of a number; iPhone needs
Add to Home Screen + notifications allowed.
