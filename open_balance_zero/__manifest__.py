# -*- coding: utf-8 -*-
{
    'name': "Trinity Open Balance Session Zero",

    'summary': """
        Set Open Balance Zero Every Time When Start
        """,

    'description': """
        Long description of module's purpose
    """,

    'author': "Joke (papatpon@trinityroots.com)",
    'website': "www.trinityroots.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'sequence': 10,
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'mail',
        'base',
        'account',
        'tr_core_update',
    ],

    # always loaded
    'data': [],
    # only loaded in demonstration mode
    'qweb': [],
    'demo': [],

}
