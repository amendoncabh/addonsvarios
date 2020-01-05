# -*- coding: utf-8 -*-
{
    "name": "Trinity Disable Database Manager",
    "summary": """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",
    "description": """
        Long description of module's purpose
    """,
    "author": "Trinity Roots Co., Ltd.",
    "website": "www.trinityroots.com",
    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    "category": "Uncategorized",
    "sequence": 15,
    "version": "0.1",
    # any module necessary for this one to work correctly
    "auto_install": False,
    "depends": ["web", "tr_core_update"],
    # always loaded
    "data": ["views/webclient_templates.xml"],
    # only loaded in demonstration mode
    "qweb": [],
    "demo": [],
}
