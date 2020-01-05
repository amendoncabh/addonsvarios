# -*- coding: utf-8 -*-
{
    "name": "Trinity Roots :: POS Pricelist cache",
    "summary": "Enable a cache on products for a lower POS loading time.",
    "website": "http://www.trinityroots.co.th/",
    "author": "Odoo Community Association (OCA)",
    "category": "Point Of Sale",
    "license": "AGPL-3",
    "version": "10.0.1.0.0",
    "application": False,
    "installable": True,
    "depends": [
        "pos_customize",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/pos_cache_data.xml",
        "data/system_parameter.xml",

        "views/pos_cache_views.xml",
        "views/pos_cache_templates.xml",
    ],
    "qweb": [
        "static/src/xml/pos_cache.xml",
    ]
}
