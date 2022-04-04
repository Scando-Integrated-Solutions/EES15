# -*- coding: utf-8 -*-
{
    'name': "Reservation Management",
    'summary': """
    """,
    'description': """
    """,
    'author': "Scando Integrated Solutions",
    'website': "www.scando.solutions",
    'contributors': [
        'Mahmoud Salah <mahmoud.salah.abdelmagied@gmail.com>',
    ],
    'category': 'sales',
    'version': '0.1',
    'depends': ['base', 'account', 'stock', 'sale', 'sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/reservation_order.xml',
        'views/product_product.xml',
        'views/stock_location.xml',
    ],
    "pre_init_hook": None,
    "post_init_hook": None,
}
