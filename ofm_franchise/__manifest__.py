# -*- coding: utf-8 -*-
{
    'name': "Trinity Roots :: OFM Franchise",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.odoo.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Trinity Roots",
    'website': "www.trinityroots.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'sequence': 10,
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'pos_customize',
        'tr_core_update',
    ],

    # always loaded
    'data': [
        'security/franchise_security.xml',
        'security/ir.model.access.csv',
        'data/system_parameter.xml',
        'data/data.xml',
        'data/cron_data.xml',
        'views/daily_summary_franchise_view.xml',
        'views/res_company_view.xml',
        'views/res_bank_view.xml',
        'views/template.xml',
        'wizards/import_monthly_summary_franchise_view.xml',
        'views/monthly_summary_franchise_view.xml',
        'views/branch_view.xml',
        'views/franchise_report.xml',
        'wizards/cal_daily_summary_franchise_view.xml',
        'wizards/summary_bank_transfer_report_view.xml',
        'wizards/detail_bank_transfer_report_view.xml',
        'wizards/export_bank_transfer_view.xml',
        'wizards/import_bank_transfer_view.xml',
        'wizards/popup_message_view.xml',
        'wizards/cal_monthly_summary_franchise_view.xml',
        'wizards/confirm_monthly_summary_franchise_view.xml',
        'wizards/monthly_summary_franchise_report_view.xml',
        'wizards/sale_summary_for_all_pos_report_view.xml',
        'wizards/franchise_master_report_view.xml',
        'wizards/agreement_master_report_view.xml',
        'views/franchise_menuitem.xml',
    ],

    # only loaded in demonstration mode
    'qweb': [],
    'demo': [],

}
