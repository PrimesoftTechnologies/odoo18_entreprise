{
    'name': 'Apex Report Part No',
    'version': '18.0.5.3.0',
    'category': 'Sales/Purchase',
    'summary': 'Apex PDF format (Arial, font sizes, logo) and custom Sales / Purchase / Delivery reports',
    'description': """
* Sales and purchase reports (Quotation, Sales Order, PO, RFQ): separate "Product Name" and "Description" columns (internal reference hidden)
* Sales order report: currency removed from line prices, dynamic Amount header
* Document reference (top right) in APEX style on Quotation / Sales Order / PO / RFQ:
  bold navy Arial, 2 lines ("Quotation No." + number); PO number always carries "PO-"
* Sales order form: "Customer Reference" renamed "Purchase Order No."
* Delivery order: Delivery Details, Delivery Terms, GRN No. and line Remarks
* Custom Delivery Note report
* Sales > Reporting > Quotation Analytic Logs: product added / updated / removed on a quotation
  (Quotation No., Customer, Product, Part No., Qty, UoM, Unit Price, Total, Reason for LOST)
* Apex PDF format: Arial, body/header/footer 14pt, table data 10pt,
  APEX HOLDINGS header 14pt uppercase, reference 16pt, logo 80px
""",
    'author': 'Apex',
    'depends': ['sale', 'purchase', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/quotation_log_views.xml',
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
