# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Trinity POS Close Session Reason',
    'version': '1.0',
    'category': 'Point of Sale',
    'sequence': 19,
    'summary': 'Trinity Close Session Reason',
    'description': """

=======================

This module allows you to manage the master data of 'Put money in'/'Take money out' reason.

""",

    'author': "Trinity Roots",
    'website': "www.trinityroots.com",

    'depends': [
        'point_of_sale',
        'pos_customize',
        'tr_core_update',
    ],
    'data': [
        'views/pos_cash_box_reason_views.xml',
        'wizards/pos_box.xml',
        'security/ir.model.access.csv',
        'views/point_of_sale_view.xml',
    ],
    'installable': True,
}
