# obama_purchase_request_internal_transfer (Odoo 18)
1. Purchase Request: Internal Transfer button ni kuu (zambarau) kabla ya transfer yoyote, kisha inakuwa ya kawaida; inafungua transfer mpya yenye locations TUPU; smart button "Transfers" yenye count.
   + smart button "Transfer" (ikishatengenezwa).
2. Inventory > Configuration > Locations: field mpya "Location Owner" (user).
3. Internal Transfer: source owner anabonyeza Validate -> Pending Validation; Validate/Mark as Todo zinafichwa kwa destination owner hadi hapo.
   -> inakuwa "Pending Validation"; owner wa destination anapata activity + message, anaweza Validate au Reject.
   Baada ya hapo process za kawaida za Odoo zinaendelea.
Hariri 'depends' kwenye __manifest__.py uweke technical name ya module ya Purchase Request.
4. Product: ukihariri na kuhifadhi product, chatter inapata log note inayoonyesha kila field iliyobadilika (zamani -> mpya).
   (Field ambazo Odoo tayari inazi-track zinaachwa ili zisijirudie.)
