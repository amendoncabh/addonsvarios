# -*- coding: utf-8 -*-
{
    "name": "Trinity Roots :: OFM - Purchase Request Customize",
    "summary": "Module summary",
    "version": "8.0.1.0.0",
    "category": "Uncategorized",
    "description": """

    MODULE
        - Purchase Request for OFM
    
    System Parameter Configuration
        - prs_api_request_token: Request Token for get Token Authentication
        - prs_api_url_request_token: URL for request Token Authentication
        - prs_api_url_check_qty: URL for check stock available from COL
        - prs_api_url_create_so: URL for create sale order at COL
        - prs_api_url_create_rtv: URL for create credit note at COL
        - prs_amount_product_per_so: Amount product per purchase order
        - prs_default_vendor: Default vendor for purchase order
        - user_api_prs: User for call api odoo, module purchase order only
    Scheduled Actions
        - Run Get Invoice For Purchase Request OFM
        - Run Get CN For Purchase Request OFM
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
        'ofm_access_right_center',
        'purchase_request',
        'purchase',
        'procurement',
        'pos_customize',
        'ofm_product_ext',
        'ofm_sync_data_staging_db',
        'web_notify',
        'tr_convert',
        'tr_core_update',
    ],
    # always loaded
    'data': [
        'security/purchase_requests_security.xml',
        'security/ir.model.access.csv',
        'data/system_parameter.xml',
        'data/cron_data.xml',
        'wizard/purchase_order_wizard_view.xml',
        'wizard/procurement_order_compute_all_view.xml',
        'wizard/suggest_fulfillment_wizard.xml',
        'views/purchase_requests_view.xml',
        'views/purchase_order_view.xml',
        'views/account_invoice_view.xml',
    ],
    'demo': [],

}