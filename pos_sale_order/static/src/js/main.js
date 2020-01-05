
odoo.define('pos_sale_order.main', function (require) {
"use strict";

var chrome = require('point_of_sale.chrome');
var core = require('web.core');

var chrome_super = chrome.Chrome.prototype;
var SoChrome = chrome.Chrome.extend({
    build_widgets: function(){
        chrome_super.build_widgets.call(this);
        this.gui.set_default_screen('sale_order_list');
        this.gui.set_startup_screen('sale_order_list');
//        this.gui.set_default_screen('sale_order_form');
//        this.gui.set_startup_screen('sale_order_form');
    },
});

core.action_registry.add('so.ui', SoChrome);
return {
    SoChrome: SoChrome
}
});
