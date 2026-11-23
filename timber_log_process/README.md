# Timber Industry (Native Odoo Integration) - v18.0.2.0.0

Module hii haitengenezi mfumo mpya. Inatumia Odoo zilizopo:

| Kazi ya Timber            | Inafanyika kwenye (Odoo standard)                         |
|---------------------------|-----------------------------------------------------------|
| Kununua magogo            | Purchase Order                                            |
| Kupokea + kupima magogo   | Receipt (stock.picking) + tab "Timber Logs" (CBM)         |
| Kila gogo                 | Lot ya Odoo (kipimo m3)                                   |
| Transit Pass (TP)         | Tab "Transit Pass (TP)" kwenye Receipt                    |
| Gharama (mafuta, usafiri) | Landed Costs (Inventory)                                  |
| Kukata mbao (sawing)      | Manufacturing Order + Bill of Materials                   |
| Board % / Waste %         | Bill of Materials (0.6 board + 0.4 waste By-Product)      |
| Mbao zilizotoka           | Tab "Timber Boards" kwenye Manufacturing Order            |
| Stock                     | Inventory (quants)                                        |
| Mauzo                     | Sales Order + Delivery                                    |
| Dashboard (cards 8)       | Timber > Dashboard, inasoma data ya Odoo moja kwa moja   |
| Reports                   | Pivot/Graph za Odoo + PDF 2 (Log Intake, Sawing)          |

Custom code iliyobaki: models 5 ndogo (timber.measurement + extension za stock.lot,
stock.picking, mrp.production, product.template).

Kubadilisha asilimia: Timber > Configuration > Sawing Ratios (Bill of Materials).
