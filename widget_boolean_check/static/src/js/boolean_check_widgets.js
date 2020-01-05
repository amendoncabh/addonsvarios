odoo.define('web.boolean_check_widgets', function (require) {
"use strict";

var core = require('web.core');
var toggle_button = core.form_widget_registry.get('toggle_button');

var toggle_button_check = toggle_button.extend({
    render_value: function () {
        var class_name = this.get_value() ? 'fa fa-check o_toggle_button_success' : 'fa fa-times text-warning';
        this.$('i').attr('class', (class_name));
    },
});

core.form_widget_registry
    .add('toggle_button_check', toggle_button_check)

return {
    ToggleButtonCheck: toggle_button_check,
};

});
