# -*- coding: utf-8 -*-
{
    'name': "Trinity Roots :: OFM Inventory Cycle Count",

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
        'ofm_template_of_product',
        'ofm_reason_code'
    ],

    # always loaded
    'data': [
        'security/stock_inventory_cycle_count_security.xml',
        'security/stock_inventory_extend_group.xml', 
        "security/ir.model.access.csv",       
        'wizards/cycle_count_report.xml',
        'wizards/cycle_count_by_dept.xml',
        'wizards/adjustment_report.xml',
        'wizards/import_counted.xml',
        'wizards/zero_qauntity_warning.xml',
        'views/cycle_count_views.xml',
        'views/stock_inventory_view.xml',
        'views/template.xml'
    ],
    # only loaded in demonstration mode
    'qweb': [],
    'demo': [],

}
