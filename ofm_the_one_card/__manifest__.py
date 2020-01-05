# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Trinity Ofm the One Card',
    'version': '1.0',
    'category': 'Point of Sale',
    'sequence': 7,
    'summary': 'POS - the one card module',
    'description': """

=======================

Add 'the one card' Field to POS Payment.

""",

    'depends': [
        'point_of_sale',
        'pos_customize',
        'pos_orders_return_product',
        'tr_core_update',
        'pos_credit_card',
        'tr_call_api',
    ],
    'author': "Trinity Roots",
    'website': "www.trinityroots.co.th",
    'data': [
        'security/ir.model.access.csv',
        'data/pos_batch.xml',
        'data/system_parameter.xml',
        'views/point_of_sale_view.xml',
        'views/the_one_card.xml',
        # 'views/sale_order_view.xml',
        'views/account_journal_view.xml',
        'views/account_bank_statement.xml',
        'views/point_template.xml',
        'views/redeem_type.xml',

    ],
    'qweb': [
        'static/src/xml/the_one_card.xml',
    ],
    'demo': [],
    'installable': True,
}
