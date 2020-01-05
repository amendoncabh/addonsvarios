# -*- coding: utf-8 -*-
# © <YEAR(S)> <AUTHOR(S)>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Trinity Roots :: OFM - Module Product Extend",
    "summary": "Module summary",
    "version": "8.0.1.0.0",
    "category": "Uncategorized",
    "description": """

add another field & method to product for ofm

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
    "depends": [
        'ofm_access_right_center',
        'base',
        'stock',
        'stock_account',
        'point_of_sale',
        'product',
        'pos_select_product',
        'tr_convert',
        'tr_core_update',
        'ofm_sync_data_staging_db',
    ],
    "data": [
        'security/ir.model.access.csv',
        'data/system_parameter.xml',
        'data/cron_data.xml',
        'data/stock_account_data.xml',
        'views/product_template_views.xml',
        'views/product_views.xml',
        'views/product_price_dropship_views.xml',
    ],
    "demo": [],
    "qweb": []
}
