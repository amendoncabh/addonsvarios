# -*- coding: utf-8 -*-
{
    'name': "Trinity Install OFM Module",

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
    'category': 'Uncategorized',
    'sequence': 15,
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'jasper_reports',
        'ofm_access_right_center',
        'tr_convert',
        'ofm_custom_product_label',
        'ofm_custom_search_in_field',
        'ofm_custom_tr_account_v10',
        'ofm_product_ext',
        'ofm_purchase_request',
        'ofm_so_ext',
        'ofm_inventory_ext',
        'ofm_point_of_sale_ext',
        'ofm_purchases_ext',
        'ofm_settings_ext',
        'open_balance_zero',
        'pos_close_session_reason',
        'pos_customize',
        'ofm_promotion',
        'ofm_ext_procurement',
        'pos_discount_on_payment',
        'pos_loyalty',
        'pos_no_change',
        'pos_printbill',
        'pos_credit_card',
        'pos_select_product',
        'pos_stock_display',
        'sequence_per_branch',
        'tr_monthly_sequence',
        'ofm_ext_tools',
        'type_of_product_pricelist',
        'pos_orders_return_product',
        'pos_order_return',
        'pos_customer_information',
        'hide_duplicate_action',
        'ofm_calculate_average_price',
        'ofm_stock_internal_move',
        'widget_allow_number',
        'widget_editable_top',
        'rd_account_invoice_detail',
        'ofm_calculate_average_price',
        'ofm_request_reverse_rd',
        'widget_many2many_tags_placeholder',
        'widget_boolean_check',
        'ofm_pricelists',
        'ofm_the_one_card',
        'ofm_sync_data_staging_db',
        'ofm_coupon',
        'web_notify',
        'sequence_per_company',
        'tr_account_deposit',
        'tr_call_api',
        'tr_customer_member',
        'pos_sale_order',
    ],

    # always loaded
    'data': [],
    # only loaded in demonstration mode
    'qweb': [],
    'demo': [],

}
