# -*- coding: utf-8 -*-
{
    'name': "Trinity Roots :: POS Customize",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.odoo.com""",

    'author': "Odoo Community Association (OCA), Joke (papatpon@trinityroots.com)",
    'website': "https://www.trinityroots.com",
    'license': "AGPL-3",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'sequence': 10,
    'version': '10.0.0.1.0',

    # any module necessary for this one to work correctly
    'depends': [
        'widget_allow_number',
        'point_of_sale',
        'pos_no_change',
        'pos_select_product',
        'pos_loyalty',
        'pos_printbill',
        'ofm_product_ext',
        'pos_stock_display',
        'tr_monthly_sequence',
        'account',
        'product',
        'report',
        'stock',
        'base',
        'sale_stock',
        'mail',
        'open_balance_zero',
        'tr_core_update',
    ],

    # always loaded
    'data': [
        'data/account_data.xml',
        'data/sequence_default.xml',

        'views/sequence.xml',

        'security/point_of_sale_security.xml',
        'security/stock_security.xml',
        'security/res_partner_security.xml',
        'security/ir.model.access.csv',

        'views/menu_report.xml',
        'views/partner_view.xml',
        'views/point_of_sale_view.xml',
        'views/point_of_sale_report.xml',
        'views/product_view.xml',
        'views/branch.xml',
        'views/company_view.xml',
        'views/stock_view.xml',
        'views/templates.xml',
        'views/requisition_of_branches_view.xml',
        'views/res_users_view.xml',
        'views/account_view.xml',
        'views/return_reason_view.xml',
        'views/point_of_sale_dashboard.xml',
        'views/pos_product_template_view.xml',

        'wizard/annual_sales_report_view.xml',
        'wizard/best_seller_for_each_branches_report_view.xml',
        'wizard/daily_sale_report_view.xml',
        'wizard/discount_by_bills_report_view.xml',
        'wizard/discount_type_report_view.xml',
        'wizard/full_tax_invoice_report_view.xml',
        'wizard/hourly_sale_volume_by_cate_view.xml',
        'wizard/net_sale_by_categories_report_view.xml',
        'wizard/payment_type_report_view.xml',
        'wizard/product_not_sale.xml',
        'wizard/report_invoice_view.xml',
        'wizard/report_receipt_short_view.xml',
        'wizard/report_sales_volume_by_branch_view.xml',
        'wizard/sale_by_day_report_view.xml',
        'wizard/sale_order_detail.xml',
        'wizard/sales_tax_report_view.xml',
        'wizard/test_net_sale_view.xml',
        'wizard/void_whole_bill_order_report_a4_view.xml',
        'wizard/wizard_change_customer_info_view.xml',
        'wizard/cashier_summary_report_view.xml',
        'wizard/sales_by_session_cashier_report_view.xml',
        'wizard/payment_type_bill_report_view.xml',
        'wizard/wizard_open_existing_session_cb_close_view.xml',
        'wizard/hourly_sale_product_line_by_cat_view.xml',
        'wizard/summary_sales_tax_report_view.xml',
        'wizard/daily_sale_summary_report_view.xml',
        'wizard/daily_sale_detail_report_view.xml',
        'wizard/stock_picking_return_view.xml',
        'wizard/confirm_create_invoice_wizard_view.xml',
        'wizard/pos_payment_view.xml',

    ],
    # only loaded in demonstration mode
    'qweb': [
        'static/src/xml/custom.xml',
        'static/src/xml/company.xml',
    ],
    'demo': [],

}