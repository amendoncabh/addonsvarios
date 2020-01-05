# -*- coding: utf-8 -*-
# © <YEAR(S)> <AUTHOR(S)>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Trinity Roots :: OFM - Custom Search Result More Than 160 Record",
    "summary": "Module summary",
    "version": "8.0.1.0.0",
    "category": "Uncategorized",
    "description": """

MODULE
======

  * When Show Result From Field Many2view Show More Than 160 Record

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
        "base",
        'web',
        'tr_core_update',
    ],
    "data": [
        'views/templates.xml',
    ],
    "demo": [],
    "qweb": []
}
