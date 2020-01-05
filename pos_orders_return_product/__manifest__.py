# -*- coding: utf-8 -*-
#################################################################################
# Author      : Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# Copyright(c): 2015-Present Webkul Software Pvt. Ltd.
# All Rights Reserved.
#
#
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#
# You should have received a copy of the License along with this program.
# If not, see <https://store.webkul.com/license.html/>
#################################################################################
{
    "name": "POS All Orders List",
    "summary": "POS All Orders List model display all old orders and this model linked with POS order reprint and POS Reorder.",
    "category": "Point Of Sale",
    "version": "3.3.2",
    "sequence": 1,
    "author": "Webkul Software Pvt. Ltd.",
    "license": "Other proprietary",
    "website": "https://store.webkul.com/Odoo-POS-All-Orders-List.html",
    "description": """https://webkul.com/blog/odoo-pos-all-orders-list/""",
    "live_test_url": "http://odoodemo.webkul.com/?module=pos_orders&version=10.0&custom_url=/pos/web",
    "depends": [
        'base',
        'point_of_sale',
        'ofm_coupon',
        'ofm_promotion',
        'tr_core_update',
    ],
    "data": [
        'data/system_parameter.xml',

        'views/pos_orders_view.xml',
        'views/template.xml',
    ],
    "demo": ['data/pos_orders_demo.xml'],
    "qweb": ['static/src/xml/pos_orders.xml'],
    "images": ['static/description/Banner.png'],
    "application": True,
    "installable": True,
    "auto_install": False,
    "price": 27,
    "currency": "EUR",
    "pre_init_hook": "pre_init_check",
}
