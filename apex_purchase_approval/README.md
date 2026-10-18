# apex_purchase_approval (Odoo 18)

Install: copy folder to your addons path, restart Odoo, Apps > Update Apps List, install "Apex Purchase Approval".

Flow: RFQ -> RFQ Sent -> Wait for Approval -> Purchase Order
1. Fill the RFQ and choose an **Approver**.
2. Click **Confirm Order** -> status becomes *Wait for Approval*.
3. Approver gets a chatter message + an Activity (clock icon).
4. Approver clicks **Approve** (-> Purchase Order) or **Reject** (-> back to RFQ with reason).

Notes:
- Approver must have at least Purchase / User access.
- For the in-app inbox notification, set the approver's Preferences > Notification = "Handle in Odoo".
