# -*- coding: utf-8 -*-
# © <YEAR(S)> <AUTHOR(S)>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Trinity Roots :: OFM Request Approve Reverse RD",
    "summary": "For updating related project modules",
    "version": "8.0.1.0.0",
    "category": "Uncategorized",
    "description": """

MODULE
======

  * This module MUST be depended by related project module.
  * If this module is updated, All related module will be updated too.

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
        'web_notify',
        'pos_customize',
        'ofm_inventory_ext',
        'tr_core_update',
    ],
    # always loaded
    'data': [
        'security/request_reverse_rd_security.xml',
        'security/ir.model.access.csv',
        'views/ofm_request_reverse_view.xml',
        'views/stock_view.xml',
        'wizard/reason_reject_wizard_view.xml',
        'wizard/reason_approve_wizard_view.xml',
    ],
}
