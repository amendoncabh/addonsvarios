# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Trinity POS No Change',
    'version': '1.0',
    'category': 'Point of Sale',
    'sequence': 7,
    'summary': 'POS - receive payment with no change button',
    'description': """

=======================

Add 'No Change' button to POS checkout page.

""",

    'depends': [
        'point_of_sale',
        'tr_core_update',
    ],
    'author': "Trinity Roots",
    'website': "www.trinityroots.com",
    'data': [
        'views/templates.xml',
    ],
    'qweb': [
        'static/src/xml/no_change.xml',
    ],
    'demo': [],
    'installable': True,
}
