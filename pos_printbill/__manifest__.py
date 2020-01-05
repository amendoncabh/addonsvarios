# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Trinity POS Bill Printing',
    'version': '1.0',
    'category': 'Point of Sale',
    'sequence': 7,
    'summary': 'bill printing ',
    'description': """

=======================

This module adds several restaurant features to the Point of Sale:
- Bill Printing: Allows you to print a receipt before the order is paid

""",

    'depends': [
        'point_of_sale',
        'tr_core_update',
    ],
    'author': "Joke (papatpon@trinityroots.com)",
    'website': "www.trinityroots.com",
    'data': [
        'views/templates.xml',
    ],
    'qweb': [
        'static/src/xml/printbill.xml',
    ],
    'demo': [],
    'installable': True,
}
