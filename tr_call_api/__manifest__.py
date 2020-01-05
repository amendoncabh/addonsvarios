# -*- coding: utf-8 -*-
{
    'name': "Trinity Roots :: TR Call API",

    'summary': """
        Call API By URL and Return Result
    """,

    'author': "Odoo Community Association (OCA), Trinityroots",
    'license': "AGPL-3",
    'website': "https://www.trinityroots.co.th",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'sequence': 10,
    'version': '10.0.0.0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'ofm_purchase_request',
        'ofm_so_ext',
        'tr_convert',
        'tr_core_update',
    ],

    # always loaded
    'data': [
        'data/res_users.xml',
    ],
    # only loaded in demonstration mode
    'qweb': [],
    'demo': [],

}