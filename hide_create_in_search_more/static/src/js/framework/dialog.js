odoo.define('hide_create_in_search_more.Dialog', function (require) {
"use strict";

var core = require('web.core');
var Widget = require('web.Widget');
var Dialog = require('web.Dialog');

var QWeb = core.qweb;
var _t = core._t;

/**
    A useful class to handle dialogs.

    Attributes:
    - $footer: A jQuery element targeting a dom part where buttons can be added. It always exists
    during the lifecycle of the dialog.
*/

Dialog.include({

    set_buttons: function(buttons) {
        var self = this;
        var session_odoo = odoo || window.odoo;
        if(!session_odoo.session_info.is_admin && buttons && buttons.length > 0){
            buttons = buttons.filter( (item) => item.text != "Create" );
        }
        this._super(buttons)
    },
});


});
