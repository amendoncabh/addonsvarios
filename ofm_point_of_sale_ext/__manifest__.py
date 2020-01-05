# -*- coding: utf-8 -*-
# © <YEAR(S)> <AUTHOR(S)>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Trinity Roots :: OFM - Module Point Of Sale Extend",
    "summary": "Module summary",
    "version": "8.0.1.0.0",
    "category": "Uncategorized",
    "description": """

add another field & method to point of sale for ofm

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
        "base",
        'pos_customize',
        'tr_core_update',
        'ofm_product_ext',
        'ofm_promotion',
    ],
    "data": [
        "data/cron_data.xml",
        "security/point_of_sale_security.xml",
        "security/ir.model.access.csv",
        "views/point_of_sale_view.xml",
        "wizards/receive_control_by_cashier_report_view.xml",
        "wizards/monthly_sales_tax_report_view.xml",
        "wizards/monthly_sales_tax_return_view.xml",
        "wizards/sales_tax_return_report_view.xml",
        "wizards/return_detail_report_view.xml",
        "wizards/summary_received_product_return_report_view.xml",
        "wizards/full_tax_instead_abb_report_view.xml",
        "wizards/return_void_receipt_listing_report_view.xml",
    ],
    "demo": [],
    "qweb": []
}
