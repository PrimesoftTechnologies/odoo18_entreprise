{
    'name': 'Oscon Purchase Order Approval',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Purchase',
    'summary': 'Submit for Approval workflow before confirming a Purchase Order',
    'description': """
Purchase Order approval workflow:
 * "Confirm Order" button is hidden until the order is approved.
 * Approvers (multiple users) are defined in Purchase > Configuration > Settings > Approvals.
 * Approvers get an activity + notification and can Approve or Reject (with reason).
 * Once approved, the buyer confirms the order and the standard Odoo flow continues.
    """,
    'author': 'Oscon',
    'depends': ['purchase', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/purchase_order_reject_wizard_views.xml',
        'views/res_config_settings_views.xml',
        'views/purchase_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
