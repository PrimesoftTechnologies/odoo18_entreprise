# Van Management System — Odoo 18

Custom Van Distribution module for Odoo 18.

## Main workflow

Warehouse → Load Request → Supervisor Approval → Van Stock → Van POS Sales → Unload Unsold Stock → Warehouse.

## Dependencies

- stock
- point_of_sale
- fleet
- mail

## User groups

1. Van Salesman
2. Van Supervisor
3. Van Distribution Manager

## Installation

Copy `van_management_system` into your Odoo custom addons path, restart Odoo, update Apps list and install the module.

## Important

This module uses Odoo Inventory (`stock.picking`, `stock.move`, `stock.location`) for actual inventory movement instead of maintaining a parallel stock engine.

The POS extension adds Van POS configuration and links a POS configuration to a van and its van stock location.

## Suggested setup

1. Install Inventory, Point of Sale and Fleet.
2. Install this module.
3. Create users and assign Van Distribution groups.
4. Create a fleet vehicle and enable "Van Distribution Vehicle".
5. Assign salesman and supervisor.
6. Create the van stock location.
7. Create/configure a POS and enable "Is Van POS".
8. Assign the POS to the van.
9. Create a Load to Van request.
10. Submit it.
11. Supervisor approves and validates the inventory transfer.
12. Open the Van POS session and sell loaded products.
13. At the end of the route, create an Unload to Warehouse request for unsold stock.
14. Supervisor approves and validates the unload transfer.

## Notes

This is a functional foundation intended to be extended with deeper POS frontend filtering, route management, customer visit planning, route reports, cash reconciliation rules, GPS integration and advanced dashboards.


=======================================================================================================
=======================================================================================================

Kwa kifupi, flow ya Van Management inaanza kwenye Route Planning, lakini stock lazima iwe tayari warehouse.

Flow nzima

1. Route → Plan Route

Chagua Van
Chagua Salesman
Weka tarehe
Weka customers/stops watakaotembelewa
Plan Route

2. Stock Loading → Load bidhaa kwenye Van

Chagua Van
Chagua products na quantities
Supervisor/Manager ana-approve
Stock inahamishwa:
Warehouse → Van

3. Start Route

Salesman anaanza route
Anaenda kwa customers waliopangwa.

4. Sales / POS

Anapofika Customer A → anafanya sale kupitia Sales Order au POS
Customer B → sale nyingine
Stock ya Van inapungua kadri anavyouza.

5. Stock Return
Mwisho wa siku/route:

Bidhaa ambazo hazijauzwa zinarudishwa:
Van → Warehouse

6. Complete Route

Route inafungwa baada ya ziara zote kukamilika.
Mfano halisi

Route
→ Kariakoo → Ilala → Buguruni

⬇️

Stock Loading
→ Van inapewa Coke 100, Water 100

⬇️

Start Route

⬇️

Customer A
→ Sales 20 Coke

⬇️

Customer B
→ Sales 30 Coke

⬇️

Customer C
→ Sales 10 Water

⬇️

Stock Return
→ Coke 50 + Water 90 zinarudi warehouse

⬇️

Complete Route

Kwa hiyo architecture yetu nzuri ni:

ROUTE → LOAD → SELL → RETURN → COMPLETE

Route ndiyo inapanga wapi van itaenda, Loading inaamua imebeba nini, Sales/POS ina-record imeuza nini, na Return ina-record kilichobaki.