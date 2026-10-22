# Asset Management Prime (`asset_management_prime`) - Odoo 18

Complete office asset lifecycle: **request -> register -> assign -> maintain -> depreciate -> audit -> dispose**.
Works on **Odoo 18 Community and Enterprise** (own depreciation engine, does not need `account_asset`).

Depends on: `base`, `mail`, `hr`, `account`.

## 1. Installation
1. Copy the `asset_management_prime` folder into your addons path.
2. Restart Odoo and run: `./odoo-bin -c odoo.conf -d <db> -i asset_management_prime`
   (or Apps -> Update Apps List -> install "Asset Management Prime").
3. Admin automatically becomes **Asset Manager**. Add other users via Settings -> Users -> *Asset Management Prime*.

## 2. Roles (security groups)
| Group | Can do |
|---|---|
| **User** | See assets, create asset requests, report a fault (maintenance request), see own assets |
| **Technician** | + start / finish maintenance, record parts & costs |
| **Auditor** | + create audits, scan assets, mark found/missing |
| **Asset Manager** | Everything: confirm assets, assign, transfer, approve, dispose, post depreciation, configuration |

Multi-company record rules are included on all main models.

## 3. First-time configuration
1. **Assets Prime -> Configuration -> Locations**: create hierarchy (Head Office / Floor 1 / Room 3).
2. **Configuration -> Categories**: for each category set method (Straight-Line, Declining Balance, Manual),
   useful life (months), salvage %, and accounts: *Journal, Asset, Accumulated Depreciation, Depreciation Expense,
   Gain/Loss on Disposal*. Tick **Auto-Post Entries** to let the cron post due depreciation.
3. Make sure employees have a department (`hr`) - departments drive approvals.

## 4. Use cases & how the module handles them
| # | Use case | Where / How |
|---|---|---|
| 1 | Configure categories, locations, numbering | Configuration menu; sequence `AST/YYYY/0001` |
| 2 | Request a new asset with approval | *Asset Requests*: Draft -> Dept. approval -> Asset Manager approval -> **Create Asset** |
| 3 | Register an asset (manual, from vendor bill, donation) | *All Assets*; pick **Vendor Bill** to auto-fill vendor/date/value |
| 4 | Bulk import | Favorites -> *Import records* on the Assets list (Excel/CSV) |
| 5 | Barcode / QR tag | Asset -> **Print Tag** (QR, 90x50 mm label) |
| 6 | Assign (check-out) / return (check-in) | Asset -> **Assign**; *Assignments* -> Check-out / Check-in; asset becomes *In Use* / *Available* |
| 7 | Handover form with signature | Assignment -> **Print Handover Form** (signature captured on the form) |
| 8 | Temporary loan with return date | Assignment type *Temporary Loan*; overdue loans highlighted + cron activity |
| 9 | Transfer between employee / department / location | *Transfers*: Submit -> Approve -> Complete (closes old assignment, opens new one) |
| 10 | Offboarding | Employee form -> **Assets** smart button lists everything the employee holds |
| 11 | Report a fault | Asset -> **Request Maintenance** (any user) |
| 12 | Corrective & preventive maintenance | *Maintenance*: New -> In Progress -> Done; asset goes *Under Maintenance* automatically |
| 13 | Recurring service | Preventive + *Recurring*: next order auto-created when done |
| 14 | Costs, spare parts, downtime | Maintenance form: labor + parts lines, downtime hours computed |
| 15 | Warranty / insurance / service alerts | Daily cron creates activities for the asset's custodian |
| 16 | Depreciation | Straight-line, declining balance, manual; schedule built on **Confirm**; **Compute Depreciation** rebuilds the unposted lines |
| 17 | Journal entries | Post line manually or by cron: Dr Expense / Cr Accumulated Depreciation |
| 18 | Net book value | On each asset and in Asset Analysis |
| 19 | Physical audit / stock take | *Audits*: scope (all / location / department / category) -> Start -> scan barcodes -> Complete |
| 20 | Missing / misplaced detection | Pending lines become *Missing* on completion; assets scanned in another location flagged *Wrong Location*; **Apply Location Corrections** |
| 21 | Disposal: sale, scrap, lost, donation | *Disposals*: Submit -> Approve -> Confirm; stops depreciation, posts final entry with gain/loss |
| 22 | Reports & dashboards | Reporting menu: Asset Analysis (graph/pivot), Warranty/Insurance Expiring, Maintenance Costs, Audit Exceptions, Depreciation Entries; PDF: Asset Card, Tag, Handover |

## 5. Asset lifecycle
`Draft -> Available -> In Use <-> Under Maintenance -> Disposed`

## 6. Disposal accounting entry
Dr Accumulated Depreciation (posted total) + Dr Receipt account (sale value) + Dr Loss (if sale < book value)
Cr Asset account (purchase value) + Cr Gain (if sale > book value).
Disposed assets are kept (status *Disposed*), never deleted.

## 7. Models
`asset.category`, `asset.location`, `asset.asset`, `asset.depreciation.line`, `asset.assignment`,
`asset.transfer`, `asset.request`, `asset.maintenance` (+ `asset.maintenance.part`),
`asset.audit` (+ `asset.audit.line`), `asset.disposal`; extension of `hr.employee`.

## 8. Cron jobs
* **Post Due Depreciation Entries** (daily) - only categories with *Auto-Post* ticked.
* **Warranty / Insurance / Maintenance / Loan Alerts** (daily) - 30-day look-ahead.

## 9. Test checklist (after install)
1. Create location + category (with accounts) -> create asset (value 1,200,000, 36 months) -> Confirm -> check schedule.
2. Assign to an employee -> print handover form -> return it.
3. Create transfer -> approve -> complete.
4. Maintenance request -> start -> done with parts -> verify asset status & cost.
5. Post first depreciation line -> check journal entry.
6. Audit: start, scan a barcode, complete, check missing/misplaced.
7. Dispose with a sale value -> verify entry and gain/loss.

## 10. Known limitations / possible extensions
* Depreciation assumes the asset currency equals the company currency.
* No direct Purchase Order integration (vendor bill link is provided). Add `purchase` as dependency and a
  hook on `stock.move`/`purchase.order.line` if you want auto-creation of assets on receipt.
* Revaluation / impairment, analytic accounts and mobile camera barcode widget are not included (good next phase).

---
### Muhtasari kwa Kiswahili
Module hii inasimamia mali za ofisi kuanzia ombi la asset, usajili, ugawaji kwa mfanyakazi, uhamisho,
matengenezo, uchakavu (depreciation) na uhasibu wake, ukaguzi (audit) hadi kuondoa asset (kuuza, kutupa, kupotea,
kutoa). Ina majukumu manne: User, Technician, Auditor, na Asset Manager.
