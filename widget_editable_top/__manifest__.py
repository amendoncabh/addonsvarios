# -*- coding: utf-8 -*-
{
    'name': "Trinity Roots - Widget One2Many Editable on Top",

    'summary': """
        Move Add an item button from bottom to top""",

    'description': """
        This module will modified tree views of One2many, and Many2many.
        The tree view will show the Add an item button to the top of the list
        
        add the parameter, widget=\"one2many_edit_on_top\", for one2many tree view
        or add the parameter, widget=\"many2many_edit_on_top\", for many2many tree view
    """,

    'website': "www.trinityroots.co.th",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'sequence': 15,
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'tr_core_update',
    ],

    # always loaded
    'data': [
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'qweb': [
    ],
    'demo': [],

}
