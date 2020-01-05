odoo.define('ofm_internal_cycle_count.edit_button', function(require){
    "use strict";

    var core = require('web.core');
    var FormView = require('web.FormView');
    var Model = require('web.DataModel');
    var _t = core._t;
    var QWeb = core.qweb;

    FormView.include({
        load_record: function(record) {
            this._super.apply(this, arguments);
            if (this.model=='stock.inventory.cycle.count'){
                if (this.get_fields_values().state=='done' || this.get_fields_values().state=='cancel'){
                    this.$buttons.find('.o_form_button_edit').remove();
                    this.$buttons.find('.o_form_button_create').remove();
                }
                else{
                    if (this.get_fields_values().is_owner==false){
                        if (this.get_fields_values().approved_user=='owner' 
                            && (this.get_fields_values().is_staff==true 
                            || (this.get_fields_values().is_manager==true && this.get_fields_values().is_owner==false))){
                            this.$buttons.find('.o_form_button_edit').remove();
                            this.$buttons.find('.o_form_button_create').remove();
                        }
                        else if (this.get_fields_values().state=='confirm' && this.get_fields_values().is_staff==true){
                            this.$buttons.find('.o_form_button_edit').remove();
                            this.$buttons.find('.o_form_button_create').remove();
                        }
                    }
                }         
            }
            if (this.model=='stock.inventory'){
                if (this.get_fields_values().state=='done' || this.get_fields_values().state=='cancel'){
                    this.$buttons.find('.o_form_button_edit').remove();
                    this.$buttons.find('.o_form_button_create').remove();
                }
            }
            
        }
        
    });
});