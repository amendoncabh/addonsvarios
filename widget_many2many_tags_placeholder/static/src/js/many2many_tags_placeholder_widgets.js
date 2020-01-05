odoo.define('web.many2many_tags_placeholder', function (require) {
"use strict";

var core = require('web.core');
var FieldMany2ManyTags = core.form_widget_registry.get('many2many_tags');

var FieldMany2ManyTags = FieldMany2ManyTags.extend({
    init: function(field_manager, node) {
        this._super(field_manager, node);
        this.data_placeholder;
    },
    render_tag: function(data) {
        this._super(data);
        if(data.length > 0){
            if(!this.data_placeholder){
                this.data_placeholder = this.$el.find('input').attr('placeholder');
            }
            this.$el.find('input').attr('placeholder', '');
        }
        else
            this.$el.find('input').attr('placeholder', this.data_placeholder);
    },
});

core.form_widget_registry
    .add('many2many_tags', FieldMany2ManyTags)

return {
    FieldMany2ManyTags: FieldMany2ManyTags,
};

});
