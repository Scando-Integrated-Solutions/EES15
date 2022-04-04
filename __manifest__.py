# -*- coding: utf-8 -*-
{
    'name': "Egyptian electronic invoice",
    'license': 'OPL-1',
    'author': "Crevisoft Corporate",
    'website': "https://www.crevisoft.com",
    'support': 'support@crevisoft.com',
    'summary': """
        E-Invoice Egypt""",
    'description': """
       Egyptian e-Invoicing odoo module for syncing odoo Clients invoices, vendor bills, debit and credit notes with Egypt Ministry of Finance and Egyptian
                Tax Authority E-Invoice system
    """,
    'category': 'Accounting/Accounting',
    'version': '22.02.22',

    # any module necessary for this one to work correctly
    'depends': ['account'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/tax_types.xml',
        'views/res_company_views.xml',
        'views/res_currency_views.xml',
        'views/res_partner_views.xml',
        'views/product_template_views.xml',
        'views/uom_views.xml',
        'views/account_tax_views.xml',
        'views/account_move_views.xml',
        'views/taxpayer_activity_code_views.xml',
        'views/tax_type_code_views.xml',
        'views/menus.xml'
    ],
    'images': ['static/description/images/banner.gif'],
    # 'live_test_url': 'https://demo.crevisoft.com',
    'price': 290.00,
    'currency': 'USD',
}
