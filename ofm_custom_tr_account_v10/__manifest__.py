# -*- coding: utf-8 -*-
{
    "name": "Trinity Roots :: OFM - Customize TR Account v10",
    "summary": "Module summary",
    "version": "8.0.1.0.0",
    "category": "Uncategorized",
    "description": """

    MODULE
    == == ==
        - Customize Partner Information for TR Account v10
    """,
    "website": "http://www.trinityroots.co.th/",
    "author": "Trinity Roots",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "external_dependencies": {
        "python": [],
        "bin": [],
    },
    # any module necessary for this one to work correctly
    'depends': [
        'account',
        'account_journal_type',
        'account_report_th',
        'account_desc_thai',
        'account_invoice_cancel',
        'account_move_void',
        'account_invoice_discount',
        'stock_account',
        'partner_information',
        'purchase',
        'ofm_purchase_request',
        'tr_core_update',
        'ofm_purchase_request',
        'account_invoice_tax_seq',
        'ofm_promotion',
        'rd_account_invoice',
        'rd_account_invoice_detail',
        'account_invoice_wht_caculate',
        'ofm_point_of_sale_ext',
        'account_payment_method',
        'account_journal_type',
        'account_reporting',
        'customer_aging_balance',
        'widget_boolean_check',
    ],
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/account_payment.xml',
        'views/payment_method_view.xml',
        'views/account_payment_view.xml',
        'wizard/account_invoice_refund_view.xml',
        'wizard/wizard_change_detail_view.xml',
        'wizard/receive_payment_approval_view.xml',
        'views/res_partner_view.xml',
        'views/account_invoice.xml',
        'views/company_view.xml',
        'views/account_view.xml',
        'views/account_move_view.xml',
        'views/account_invoice_view.xml',
        'views/account_statement_view.xml',
        'wizard/account_invoice_refund_view.xml',
        'wizard/wizard_change_detail_view.xml',
        'wizard/wizard_vat_report.xml',
        'views/account_billing_note_view.xml',
    ],
    'demo': [],

}