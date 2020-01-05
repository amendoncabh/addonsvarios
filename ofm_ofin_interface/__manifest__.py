# -*- coding: utf-8 -*-
{
    'name': "Trinity Roots :: OFM Interface Data To OFIN",

    'summary': """
        prepare
        """,

    'description': """
        Long description of module's purpose
    """,

    'author': "Trinityroots",
    'website': "www.trinityroots.co.th",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'sequence': 10,
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'tr_core_update',
        'ofm_custom_tr_account_v10',
    ],

    # always loaded
    'data': [
        'data/system_parameter.xml',
        'data/cron_data.xml',
        'views/account_invoice_view.xml',
        'views/company_view.xml',
        'views/res_partner_view.xml',
    ],
    # only loaded in demonstration mode
    'qweb': [],
    'demo': [],

}