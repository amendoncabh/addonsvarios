odoo.define('web.Sidebar.fix.duplicate', function (require) {
"use strict";
    var core = require('web.core');
    var data = require('web.data');
    var Dialog = require('web.Dialog');
    var framework = require('web.framework');
    var pyeval = require('web.pyeval');
    var Widget = require('web.Widget');

    var QWeb = core.qweb;
    var _t = core._t;

    var Sidebar = require('web.Sidebar');

    Sidebar.include({
        start: function(){
            var self = this;
            var session_odoo = odoo || window.odoo;
            if(!session_odoo.session_info.is_admin && self.items && self.items.other){
                self.items.other = self.items.other.filter( (item) => item.label !="Duplicate" );
            }
            this._super(this)
        },
    });
});