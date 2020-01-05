# -*- coding: utf-8 -*-
{
    'name': "Trinity Roots :: OFM Stock Internal Move",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.odoo.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "trinityroots.co.th",
    'website': "trinityroots.co.th",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'sequence': 10,
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'ofm_access_right_center',
        'stock',
        'pos_customize',
        'web_notify',
        'tr_core_update',
    ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/stock_internal_move_security.xml',

        'views/ofm_stock_internal_move_views.xml',
    ],
    # only loaded in demonstration mode
    'qweb': [],
    'demo': [],

}