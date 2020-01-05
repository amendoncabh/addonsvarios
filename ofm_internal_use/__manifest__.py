# -*- coding: utf-8 -*-
{
    'name': "Trinity Roots :: OFM Inventory Internal Use",

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
        'ofm_inventory_ext',
        'ofm_reason_code',
        'ofm_internal_use_reason',
        'stock',
        'base'      
    ],

    # always loaded
    'data': [
        'wizards/internal_use_report.xml',
        'security/internal_use_security.xml', 
        "security/ir.model.access.csv",        
        'views/internal_use_view.xml',
        'views/template.xml'
    ],
    # only loaded in demonstration mode
    'qweb': [],
    'demo': [],

}
