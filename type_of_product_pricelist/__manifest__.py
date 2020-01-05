# -*- coding: utf-8 -*-

{
    "name": "Trinity Roots :: OFM - Type Of Product Price List",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    "author": "Trinity Roots",
    "website": "http://www.trinityroots.co.th/",
    "license": "AGPL-3",
    "application": False,
    "installable": True,

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Point of Sale',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'point_of_sale',
        'tr_core_update',
    ],

    # always loaded
    'data': [
        'views/product_pricelist_view.xml',
    ],
    # only loaded in demonstration mode
    # 'qweb': ['static/src/xml/pos.xml'],
    'demo': [],

}
