# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Trinity POS Loyalty Program',
    'version': '1.0',
    'category': 'Point of Sale',
    'sequence': 19,
    'summary': 'Trinity Loyalty Program for the Point of Sale ',
    'description': """

=======================

This module allows you to define a loyalty program in
the point of sale, where the customers earn loyalty points
and get rewards.

""",

    'author': "Joke (papatpon@trinityroots.com)",
    'website': "www.trinityroots.com",

    'depends': [
        'point_of_sale',
        'pos_select_product',
        'tr_core_update',
    ],
    'data': [
        'views/views.xml',
        'security/ir.model.access.csv',
        'views/templates.xml'
    ],
    'qweb': ['static/src/xml/loyalty.xml'],
    'demo': [
        'loyalty_demo.xml',
    ],
    'installable': True,
}
