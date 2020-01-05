# -*- coding: utf-8 -*-
{
    'name': "Trinity Roots :: OFM Procurement Extend",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.odoo.com""",

    'description': """
        Long description of module's purpose
    """,

    "author": "Trinity Roots",
    "license": "AGPL-3",
    'website': "www.trinityroots.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'sequence': 10,
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'pos_customize',
        'tr_core_update',
    ],

    # always loaded
    'data': [],
    # only loaded in demonstration mode
    'qweb': [],
    'demo': [],

}