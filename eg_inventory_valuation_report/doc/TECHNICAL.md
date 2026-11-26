# Inventory Valuation Report — Technical Documentation

Module: `eg_inventory_valuation_report` · Odoo 18.0 Enterprise · version 18.0.18.33.0

## 1. Architecture

```
wizard  inventory.valuation.report (TransientModel)
   │  validates parameters (companies, dates, scope, locations) server-side
   ▼
engine  eg.inventory.valuation.engine (AbstractModel) ── _build_dataset(params) ──► dataset (dict)
   │                                                                          │
   ├── PDF  : report.eg_inventory_valuation_report.stock_inventory_pdf_report ◄┤  (QWeb, landscape)
   └── XLSX : report/valuation_xlsx.py  InventoryValuationXlsx(env, dataset) ◄─┘  (xlsxwriter)
```

* One dataset, two renderers. Renderers never calculate figures; Excel formulas
  only re-aggregate engine figures and carry the engine value as cached result.
* Files: `models/inventory_valuation_engine.py` (all calculations),
  `wizard/inventory_valuation_report.py` (parameters, actions),
  `report/valuation_pdf.py`, `reports/inventory_valuation_pdf_report.xml` (PDF),
  `report/valuation_xlsx.py` (Excel + shared methodology wording),
  `tests/test_inventory_valuation_report.py` (24 scenario tests).

## 2. Source of truth

| Scope | Quantities | Values | Status |
|---|---|---|---|
| Company (default) | `stock.valuation.layer.quantity` | `stock.valuation.layer.value` | **Authoritative** — identical to Odoo's Valuation report and `product.value_svl` |
| Per warehouse / locations | done `stock.move.line.quantity_product_uom` | allocation (see §5) | **Estimated**, flagged everywhere |

Historical value is never `qty × current cost`: each layer carries the value
recorded at the time (FIFO layer cost, AVCO average at that moment, standard
price in force), and later revaluations are separate layers dated when they happened.

## 3. Period logic (company scope)

All layers with `create_date < end_of(date_to)` are read once and bucketed:

* `create_date < start_of(date_from)` → **opening**
* otherwise → a movement type (table below) → **incoming / outgoing / adjustment**

`closing = Σ all layers` = opening + incoming − outgoing + adjustments, exactly,
for quantities and values (Decimal arithmetic, rounded once per figure).
Day boundaries are local midnights in the user's time zone, converted to UTC.
"As of" reports put every layer in the balance and list no movement.

**Date basis "journal entry date"**: a layer is dated by its journal entry
(`account_move.date`) when it has one (automated valuation), otherwise by its
local creation date. Useful for back-dated accounting entries. The native
valuation check is then not applicable and reported as such.

### Movement classification (one bucket per layer)

| Layer | Condition (counterpart location of the layer's move) | Bucket |
|---|---|---|
| qty = 0 | `stock_landed_cost_id` set | Landed costs (adj.) |
| qty = 0 | `account_move_line_id` set | Vendor bill price differences (adj.) |
| qty = 0 | no stock move | Revaluations & standard cost changes (adj.) |
| qty = 0 | other | Negative-stock & other corrections (adj.) |
| qty ≠ 0 | no stock move | Costing method / category change (adj., pairs net to 0 qty) |
| qty > 0 | from supplier / customer / inventory / production / transit / other company | Purchase / customer return / inventory gain / manufacturing (or unbuild) / transit / inter-company |
| qty < 0 | to customer / supplier / scrap / inventory / production / transit / other company | Delivery / vendor return / scrap / inventory loss / consumption (or unbuild) / transit / inter-company |
| dropship | supplier → customer | Dropship in + Dropship out (Odoo creates both layers) |

Internal transfers within a company create no layer and therefore never inflate
incoming/outgoing at company level.

## 4. Controls produced with every report

1. **Native check** — closing value vs `product.value_svl` computed by Odoo's ORM at the end date (must be 0 difference).
2. **Physical vs valued quantity** — quantity from done move lines in the company's valued locations (internal + company transit; consignment and subcontractor locations excluded) vs layer quantity, per product. Differences are listed as exceptions (e.g. stock counted before `stock_account` was installed).
3. **General ledger** (automated valuation, unfiltered reports, user with accounting read access) — inventory value per stock valuation account vs posted GL balance at the end date. Differences are reported, never forced.
4. **Allocated vs authoritative** (warehouse/location scope) — sum of allocated sections vs company valuation.
5. **Row exceptions** — negative stock, value without quantity, quantity without value, opposite signs, rounding residual.

## 5. Warehouse / location allocation (estimated)

Odoo values stock per company. For location views:

* quantities: done move lines crossing the section boundary (product UoM, consignment excluded);
* valued moves (with layers): actual unit cost = Σ layer value / Σ layer qty of that move;
* unvalued internal transfers: company average cost at the transfer time (cumulative layers);
* opening / closing: quantity × company average unit cost at the boundary (fallback: last layer unit cost);
* residual (landed costs, revaluations, FIFO layer mix) → "Cost allocation effect (estimated)".

Consolidated totals eliminate transfers between the reported sections (explicit
"Less: transfers between reported sections" line in Excel).

## 5b. Location sheets (classic layout, Excel)

* Option "Excel: One Sheet per Location" (default on). Locations empty = **all** stock locations.
* One sheet per location: each selected location, or every top-level stock location when none is
  selected; sub-locations roll into their nearest selected/top-level ancestor (counted once).
* Columns as the original report: Product, Costing, Begin, In, Out, Internal, Adjust, End (Qty/Value).
  In/Out = external (suppliers, customers, production, other companies); Internal = net transfers with
  other company locations; Adjust = inventory counts and scrap (qty) + value-only effects; End is an
  Excel formula `Begin + In - Out + Internal + Adjust` (cached = engine value).
* "All Locations" sheet: products summed over all location sheets, a summary by location (formulas
  linked to each sheet's grand total) and the difference to the company valuation per Odoo books.
* Figures come from the same allocation engine as the location scope (`_build_location_sheets`).

## 5c. Simple report (toggle)

* Wizard toggle **Simple Report** switches the form to: Start/End date, Companies, Locations (empty = all),
  optional categories/products. Print PDF and Export Excel then use the simple layout.
* Layout = the original report exactly: title, location, `Company: …`, `Period: …`, the 14 columns
  (Product, Costing, Begin/In/Out/Internal/Adjust/End Qty+Value), zebra rows, GRAND TOTAL.
* One sheet (Excel) / page (PDF) per location, sorted by name; "All Locations" first when there are
  several (with the company value per Odoo books). Both come from `report/simple_report.py:simple_blocks`.
* Figures = the location sheets of the engine (period report, every product with a balance or movement).

## 6. Security

* Wizard and menu: `stock.group_stock_manager` (same as native valuation layers).
* Engine refuses users without read access on `stock.valuation.layer` (no `sudo()`).
* Companies are validated against `user.company_ids`; selections are read without
  record-rule filtering so that a forbidden company is **refused**, not silently
  replaced (relational fields carry no field-level domain for that reason).
* Products, locations, warehouses come from ORM searches (record rules apply);
  SQL is parameterised and restricted to validated company ids and those ids.
* GL comparison uses `account.move.line._read_group` (rules apply) and is skipped
  without accounting read access.

## 7. Performance

* Company valuation: one aggregate query over layers (uses the native
  `stock_valuation_layer` indexes; 66k layers in ~0.2 s). Total dataset for
  2,000 products ≈ 1.5–3.8 s and ~12–96 queries independent of product count.
* No N+1: product/category data read in batch; no per-product queries.
* No new database index was required (plan uses existing product/company indexes).
* Excel generation is bound by xlsxwriter serialisation (~10–15k cells/s);
  for very large catalogues use Summary level or category filters.

## 8. Extending

* New movement type: add it to `MOVEMENT_TYPES` and to `_bucket_case_sql`.
* Additional unvalued location types: extend `_unvalued_location_domain`.
* Run tests: `odoo -d <test_db> -u eg_inventory_valuation_report --test-enable --test-tags /eg_inventory_valuation_report --stop-after-init --http-port=<free port>`
