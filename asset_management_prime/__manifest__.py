{
    'name': 'Asset Management Prime',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Assets',
    'summary': 'Complete office asset lifecycle: acquisition, assignment, maintenance, depreciation, audit and disposal',
    'description': """
Asset Management Prime
======================
* Asset register with categories, locations, barcode/QR tags
* Asset requests with approval workflow
* Assignment (check-out / check-in), handover form, transfers
* Preventive & corrective maintenance with costs and downtime
* Depreciation (straight-line, declining balance, manual) with journal entries
* Physical audit / stock take with barcode scanning
* Disposal (sale, scrap, lost, donation) with gain/loss accounting
* Dashboards, pivot/graph reports, PDF reports, cron alerts
    """,
    'author': 'Your Company',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'hr', 'account'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'security/rules.xml',
        'data/sequence_data.xml',
        'data/cron_data.xml',
        'views/asset_category_views.xml',
        'views/asset_location_views.xml',
        'views/asset_views.xml',
        'views/asset_depreciation_views.xml',
        'views/asset_assignment_views.xml',
        'views/asset_transfer_views.xml',
        'views/asset_request_views.xml',
        'views/asset_maintenance_views.xml',
        'views/asset_audit_views.xml',
        'views/asset_disposal_views.xml',
        'report/asset_reports.xml',
        'report/asset_report_templates.xml',
        'views/menus.xml',
    ],
    'application': True,
    'installable': True,
}
