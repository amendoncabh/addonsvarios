odoo.define('ofm_internal_use.edit_button', function(require){
    "use strict";

    var core = require('web.core');
    var FormView = require('web.FormView');
    var Model = require('web.DataModel');
    var _t = core._t;
    var QWeb = core.qweb;

    FormView.include({
        load_record: function(record) {
            this._super.apply(this, arguments);
            if (this.model=='internal.use'){
                console.log(this.get_fields_values().state)
                if (this.get_fields_values().state=='done' || this.get_fields_values().state=='cancel'){
                    this.$buttons.find('.o_form_button_edit').remove();
                    this.$buttons.find('.o_form_button_create').remove();
                }
            }
            
        }
        
    });
});