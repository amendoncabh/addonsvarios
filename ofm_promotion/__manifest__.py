# -*- coding: utf-8 -*-
{
    "name": "Trinity Roots :: OFM - Promotion Customize",
    "summary": "Module summary",
    "version": "8.0.1.0.0",
    "category": "Uncategorized",
    "description": """

    MODULE
    == == ==
        - Promotion for OFM
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
        'base',
        'point_of_sale',
        'pos_customize',
        'ofm_coupon',
        'tr_core_update',
    ],
    # always loaded
    'data': [
        'data/data_pos_promotion_tier.xml',
        'data/system_parameter.xml',
        'security/ir.model.access.csv',
        'wizard/promotion_by_cate_view.xml',
        'wizard/promotion_by_pro_view.xml',
        'wizard/import_promotion_view.xml',
        'views/point_of_sale_view.xml',
        'views/templates.xml',
        'views/promotion_tier_view.xml',
        'views/promotion.xml',
        'views/pos_promotion_condition_view.xml',
        'views/branch.xml',
    ],
    'qweb': [
        'static/src/xml/promotion.xml',
    ],
    'demo': [],

}