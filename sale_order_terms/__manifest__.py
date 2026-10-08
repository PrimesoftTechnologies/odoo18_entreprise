{
    'name': 'Custom Sales Terms & Conditions',
    'version': '18.1',
    'category': 'Sales',
    'summary': 'custom sales terms and conditions/sales terms and conditions/terms and conditions/quotation terms/sale order terms/custom T&C/sales T&C/sale terms/quotation T&C/sales',
    'description': """In standard Odoo, terms and conditions shown in the Sale Order usually come from the Invoicing 
    or Accounting settings. But in many businesses, the sales team wants to use different terms that are specific to 
    sales deals, promotions, return policies, or delivery timelines — not related to accounting or payment rules.
    This module solves that problem by giving you a separate place inside the Sales module to add and manage your 
    Sales Terms & Conditions.Once configured, these terms will:Appear on the Sales Order screen Show up in the 
    PDF or printed version of the Sale Order Be shared with customers automatically during the sales process This way, 
    your sales team stays in control of what they want to communicate with the customer, 
    without needing help from the accounting team.""",
    'author': 'AppsComp Widgets Pvt Ltd',
    'company': 'AppsComp Widgets Pvt Ltd',
    'website': 'https://www.appscomp.com',
    'images': ['static/description/banner.png'],
    'license': 'LGPL-3',
    'depends': ['sale','sale_management', 'web'],
    'data': [
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
}
