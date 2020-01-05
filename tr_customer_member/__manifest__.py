# -*- coding: utf-8 -*-
{
    'name': "Trinity Roots :: Customer Member",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.odoo.com""",

    'description': """
        - Customer Code
        - Payment Type
        - Billing Condition
    """,

    'author': "Trinity Roots",
    'website': "www.trinityroots.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'sequence': 10,
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'ofm_access_right_center',
        'base',
        'pos_customize',
        'partner_information',
        'customer_aging_balance',
        'web_notify',
        'tr_core_update',
    ],

    # always loaded
    'data': [
        'views/res_partner.xml',
    ],
    # only loaded in demonstration mode
    'qweb': [],
    'demo': [],

}