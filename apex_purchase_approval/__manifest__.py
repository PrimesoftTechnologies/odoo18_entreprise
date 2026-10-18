{
    'name': 'Apex Purchase Approval',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Purchase',
    'summary': 'Add a "Wait for Approval" step to Purchase Orders with approver notifications',
    'description': """
Apex Purchase Approval
======================
* Status bar: RFQ > RFQ Sent > Wait for Approval > Purchase Order
* Confirm Order sends the order to "Wait for Approval"
* Only the assigned approver can Approve or Reject
* Approver is notified in the chatter (Send message) and via an Activity (clock icon)
""",
    'author': 'Apex',
    'license': 'LGPL-3',
    'depends': ['purchase', 'mail'],
    'data': [
        'views/purchase_order_views.xml',
        'wizard/purchase_reject_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
}
