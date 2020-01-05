# -*- coding: utf-8 -*-
{
    'name': "Trinity Roots :: POS Sale Order",

    'summary': """
        Sale Order module on POS
    """,

    'author': "Odoo Community Association (OCA), Trinity Roots",
    'website': "https://www.trinityroots.co.th",
    'license': "AGPL-3",
    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'sequence': 10,
    'version': '0.1',
    'version': '10.0.0.0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'ofm_access_right_center',
        'sales_team',
        'ofm_promotion',
        'tr_core_update',
    ],

    # always loaded
    'data': [
        'data/system_parameter.xml',
        'security/ir.model.access.csv',
        'security/pos_sale_order_security.xml',
        'views/sale_config.xml',
        'views/sale_session.xml',
        'views/sale_template.xml',
    ],
    # only loaded in demonstration mode
    'qweb': [
        'static/src/xml/pos_sale_order.xml',
    ],
    'demo': [],

}