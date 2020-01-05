# -*- coding: utf-8 -*-
{
    'name': "Trinity Roots :: OFM Custom Products Label",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.odoo.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "James (rapheephat@trinityroots.com)",
    'website': "www.trinityroots.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'sequence': 10,
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'product',
        'pos_select_product',
        'pos_customize',
        'tr_core_update',
    ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/re_product_label_security.xml',
        'data/report_paperformat_data.xml',
        'wizards/product_label_view.xml',
        'views/product_views.xml',
        'views/product_label_reprint_view.xml',
        'report/product_product_templates.xml',
    ],
    # only loaded in demonstration mode
    'qweb': [],
    'demo': [],

}