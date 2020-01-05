# -*- coding: utf-8 -*-
{
    'name': "Salary Employee",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.odoo.com""",

    'author': "Prakon.wir@trinityroots.co.th",
    'website': "https://www.trinityroots.com",
    'license': "AGPL-3",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'sequence': 10,
    'version': '10.0.0.1.0',

    # any module necessary for this one to work correctly
    'depends': ['base',
                'hr_contract',
    ],

    # always loaded
    'data': [],
    # only loaded in demonstration mode
    'qweb': [
    ],
    'demo': [],

}