# -*- coding: utf-8 -*-
{
    'name': "Trinity Roots :: OFM SO Extend",

    'summa  ry': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.odoo.com""",

    'author': "Odoo Community Association (OCA)",
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
        'ofm_access_right_center',
        'base',
        'account',
        'pos_customize',
        # 'ofm_the_one_card',
        'point_of_sale',
        'tr_customer_member',
        'customer_aging_balance',
        'sale',
        'sales_team',
        'sale_stock',
        'ofm_product_ext',
        'ofm_purchase_request',
        'ofm_ext_procurement',
        'pos_sale_order',
        'web_notify',
        'tr_core_update',
    ],

    # always loaded
    'data': [
        'data/system_parameter.xml',
        'data/cron_data.xml',
        'data/product_product.xml',
        'security/sale_order_security.xml',
        'security/ir.model.access.csv',
        'wizards/full_tax_invoice_report_wizard_view.xml',
        'wizards/stock_picking_return_view.xml',
        'wizards/return_product_report_wizard_view.xml',
        'wizards/receive_control_sale_backend_report_view.xml',
        'wizards/receive_control_sale_all_report_view.xml',
        'wizards/debtor_outstanding_sales_report_view.xml',
        'wizards/debtor_aged_analysis_sales_report_view.xml',
        'wizards/debtor_aging_outstanding_sales_report_view.xml',
        'wizards/products_sales_report_view.xml',
        'wizards/deposit_sales_all_cashier_report_view.xml',
        'wizards/deposit_clearing_sales_report_view.xml',
        'wizards/deposit_return_sales_report_view.xml',
        'wizards/deposit_outstanding_sales_report_view.xml',
        'wizards/products_sales_report_view.xml',
        'wizards/debtor_outstanding_sales_report_view.xml',
        'wizards/debtor_aged_analysis_sales_report_view.xml',
        'views/sale_order_view.xml',
        'views/purchase_order.xml',
        'views/res_partner.xml',
        'views/account_invoice_view.xml',
    ],
    # only loaded in demonstration mode
    'qweb': [],
    'demo': [],

}