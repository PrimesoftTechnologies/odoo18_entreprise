{
    'name': 'Apex Report Part No',
    'version': '18.0.3.0.0',
    'category': 'Sales/Purchase',
    'summary': 'Apex PDF format (Arial, font sizes, logo) and custom Sales / Purchase / Delivery reports',
    'description': """
* Sales and purchase reports show the product name only (no internal reference)
* Sales order report: currency removed from line prices, dynamic Amount header
* Sales order form: "Customer Reference" renamed "Purchase Order No."
* Delivery order: Delivery Details, Delivery Terms, GRN No. and line Remarks
* Custom Delivery Note report
* Apex PDF format: Arial, body/header/footer 8pt, table data 7.4pt,
  APEX HOLDINGS header 10pt uppercase, reference 14pt, smaller logo
""",
    'author': 'Apex',
    'depends': ['sale', 'purchase', 'stock'],
    'data': [
        'views/sale_report_templates.xml',
        'views/purchase_report_templates.xml',
    ],
    'assets': {
        'web.report_assets_common': [
            'apex_report_part_no/static/src/css/apex_report_format.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
