# -*- coding: utf-8 -*-
{
    'name': "Trinity Roots :: OFM Internal Use Reason",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.odoo.com""",

    'author': "Odoo Community Association (OCA), Trinity Roots",
    'license': "AGPL-3",
    'website': "https://www.trinityroots.co.th",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'sequence': 10,
    'version': '10.0.0.0.1',

    # any module necessary for this one to work correctly
    'depends': ['account'],

    # always loaded
    'data': [
        'views/internal_use_reason.xml',
        'security/ir.model.access.csv',
        'security/internal_use_reason_security.xml',
    ],
    # only loaded in demonstration mode
    'qweb': [],
    'demo': [],

}