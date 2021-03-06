# -*- coding: utf-8 -*-
{
    'name': "Trinity POS Select Product",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Joke (papatpon@trinityroots.com)",
    'website': "www.trinityroots.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Point of Sale',
    'sequence': 6,
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'point_of_sale',
        'ofm_sync_data_staging_db',
        'product',
        'tr_core_update',
    ],

    # always loaded
    'data': [
        'views/views.xml',
        'data/cron_data.xml',
        'data/system_parameter.xml',
        # 'security/ir.model.access.csv',
        'views/templates.xml',
        'security/pos_product_template.xml'
    ],
    # only loaded in demonstration mode
    # 'qweb': ['static/src/xml/pos.xml'],
    'demo': [],

}
