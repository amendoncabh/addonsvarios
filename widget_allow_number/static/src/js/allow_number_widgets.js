odoo.define('web.allow_number_widget', function (require) {
"use strict";

var core = require('web.core');
var FieldChar = core.form_widget_registry.get('char');
var FieldFloat = core.form_widget_registry.get('float');
var FieldMonetary = core.form_widget_registry.get('monetary');

var AllowNumber = FieldChar.extend({
    renderElement: function() {
        this._super();
        var self = this;
        if(this.$el){
            this.$el.on('keypress', function(event){
                if( !(event.key == '0' || event.key == '1' || event.key == '2' || event.key == '3'
                    || event.key == '4' || event.key == '5' || event.key == '6' || event.key == '7'
                    || event.key == '8' || event.key == '9') ){
                    event.preventDefault();
                }
            });
        }
    },
});

var FloatAllowNumber = FieldFloat.extend({
    renderElement: function() {
        this._super();
        var self = this;
        if(this.$el){
            this.$el.on('keypress', function(event){
                if( !(event.key == '0' || event.key == '1' || event.key == '2' || event.key == '3'
                    || event.key == '4' || event.key == '5' || event.key == '6' || event.key == '7'
                    || event.key == '8' || event.key == '9' || event.key == '.' || event.key == '-') ){
                    event.preventDefault();
                }
            });
        }
    },
});

var MonetaryAllowNumber = FieldMonetary.extend({
    renderElement: function() {
        this._super();
        var self = this;
        if(this.$el){
            this.$el.on('keypress', function(event){
                if( !(event.key == '0' || event.key == '1' || event.key == '2' || event.key == '3'
                    || event.key == '4' || event.key == '5' || event.key == '6' || event.key == '7'
                    || event.key == '8' || event.key == '9' || event.key == '.' || event.key == '-') ){
                    event.preventDefault();
                }
            });
        }
    },
});

core.form_widget_registry
    .add('allow_number', AllowNumber)
    .add('float_allow_number', FloatAllowNumber)
    .add('monetary_allow_number', MonetaryAllowNumber)

return {
    AllowNumber: AllowNumber,
    FloatAllowNumber: FloatAllowNumber,
    MonetaryAllowNumber: MonetaryAllowNumber,
};

});
