# -*- coding: utf-8 -*-
{
    'name': "Trinity Sequence Per Comapny",

    'summary': """
        Create Sequence By Company
        """,

    'description': """
        Long description of module's purpose
    """,

    'author': "Trinity Roots",
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
        'pos_customize',
        'tr_core_update',
    ],

    # always loaded
    'data': [
        'data/sequence_default.xml',
        'security/ir.model.access.csv'
    ],
    # only loaded in demonstration mode
    'qweb': [],
    'demo': [],

}
