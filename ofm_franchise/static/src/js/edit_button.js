odoo.define('ofm_franchise.edit_button', function(require){
    "use strict";

    var core = require('web.core');
    var FormView = require('web.FormView');
    var Model = require('web.DataModel');
    var _t = core._t;
    var QWeb = core.qweb;

    FormView.include({
        load_record:async function(record) {
            this._super.apply(this, arguments);
            if (this.model=='daily.summary.franchise'){
                var flag;
                await new Model('daily.summary.franchise').call("get_can_edit").then(function(result){
                    flag = result;
                })
                console.log(flag)
                console.log(this.get_fields_values().state)
                if (this.get_fields_values().state=='verify' && flag == false){
                    this.$buttons.find('.o_form_button_edit').css({"display":"none"});
                }
                if (this.get_fields_values().state=='active'){
                    this.$buttons.find('.o_form_button_edit').css({"display":"none"});
                }
                if (this.get_fields_values().state=='cancel'){
                    this.$buttons.find('.o_form_button_edit').css({"display":"none"});
                }
            }
            
        }
        
    });
});