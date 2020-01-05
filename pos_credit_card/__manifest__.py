# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Trinity POS Credit Card',
    'version': '1.0',
    'category': 'Point of Sale',
    'sequence': 7,
    'summary': 'POS - receive payment with credit card',
    'description': """

=======================

Add 'Credit Card No' Field to POS Payment.

""",

    'depends': [
        'point_of_sale',
        'pos_customize',
        'pos_orders_return_product',
        'tr_core_update',
    ],
    'author': "Trinity Roots",
    'website': "www.trinityroots.com",
    'data': [
        'views/account_view.xml',
        'views/credit_card_view.xml',
    ],
    'qweb': [
        'static/src/xml/credit_card.xml',
    ],
    'demo': [],
    'installable': True,
}
