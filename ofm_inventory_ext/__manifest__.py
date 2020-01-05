# -*- coding: utf-8 -*-
{
    'name': "Trinity Roots :: OFM Inventory Extend",

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
    'depends': [
        'stock',
        'stock_account',
        'pos_customize',
        'ofm_stock_internal_move',
        'tr_core_update',
    ],

    # always loaded
    'data': [
        'data/stock_data.xml',
        'security/stock_picking_type_security.xml',
        'security/stock_warehouse_orderpoint_security.xml',
        'wizards/daily_receive_doc_report_view.xml',
        'views/stock_inventory.xml',
        'views/stock_view.xml',
        'views/product_category.xml',
        'views/stock_warehouse_views.xml',
        'wizards/product_balance_report_view.xml',
        'views/stock_quant_views.xml',
        'views/stock_config_settings_views.xml',
        'views/stock_move_views.xml',
        'wizards/daily_return_detail_report_view.xml',
        'wizards/data_inventory_report_view.xml',
        'wizards/raw_data_sales_report_view.xml',
        'wizards/stock_on_hand_report_view.xml',
        'wizards/stock_move_report_view.xml',
        'wizards/stock_change_product_qty_views.xml',
    ],
    # only loaded in demonstration mode
    'qweb': [],
    'demo': [],

}