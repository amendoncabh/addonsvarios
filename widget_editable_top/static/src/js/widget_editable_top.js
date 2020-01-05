odoo.define('web.widget_editable_top', function (require) {
"use strict";

var ControlPanel = require('web.ControlPanel');
var core = require('web.core');
var data = require('web.data');
var Dialog = require('web.Dialog');
var common = require('web.form_common');
var ListView = require('web.ListView');
require('web.ListEditor'); // one must be sure that the include of ListView are done (for eg: add start_edition methods)
var Model = require('web.DataModel');
var session = require('web.session');
var utils = require('web.utils');
var ViewManager = require('web.ViewManager');

var _t = core._t;
var QWeb = core.qweb;
var COMMANDS = common.commands;
var list_widget_registry = core.list_widget_registry;

var form_relational = require('web.form_relational');
var AbstractManyField = form_relational.AbstractManyField;

/**
 * A Abstract field for one2many and many2many field
 * For all fields on2many or many2many:
 *  - this.get('value') contains a list of ids and virtual ids
 *  - get_value() return an odoo write command list
 */
var FieldX2Many = AbstractManyField.extend({
    multi_selection: false,
    disable_utility_classes: true,
    x2many_views: {},
    view_options: {},
    default_view: 'tree',
    init: function(field_manager, node) {
        this._super(field_manager, node);

        this.is_loaded = $.Deferred();
        this.initial_is_loaded = this.is_loaded;
        this.is_started = false;
        this.set_value([]);
    },
    start: function() {
        this._super.apply(this, arguments);
        var self = this;

        this.load_views();
        var destroy = function() {
            self.is_loaded = self.is_loaded.then(function() {
                self.renderElement();
                self.viewmanager.destroy();
                return $.when(self.load_views()).done(function() {
                    self.reload_current_view();
                });
            });
        };
        this.is_loaded.done(function() {
            self.on("change:effective_readonly", self, destroy);
        });
        this.view.on("on_button_cancel", this, destroy);
        this.is_started = true;
        this.reload_current_view();
    },
    load_views: function() {
        var self = this;

        var view_types = this.node.attrs.mode;
        view_types = !!view_types ? view_types.split(",") : [this.default_view];
        var views = [];
        _.each(view_types, function(view_type) {
            if (! _.include(["list", "tree", "graph", "kanban"], view_type)) {
                throw new Error(_.str.sprintf(_t("View type '%s' is not supported in X2Many."), view_type));
            }
            var view = {
                view_id: false,
                view_type: view_type === "tree" ? "list" : view_type,
                fields_view: self.field.views && self.field.views[view_type],
                options: {},
            };
            if(view.view_type === "list") {
                _.extend(view.options, {
                    action_buttons: false, // to avoid 'Save' and 'Discard' buttons to appear in X2M fields
                    addable: null,
                    selectable: self.multi_selection,
                    sortable: true,
                    import_enabled: false,
                    deletable: true
                });
                if (self.get("effective_readonly")) {
                    _.extend(view.options, {
                        deletable: null,
                        reorderable: false,
                    });
                }
            } else if (view.view_type === "kanban") {
                _.extend(view.options, {
                    action_buttons: true,
                    confirm_on_delete: false,
                });
                if (self.get("effective_readonly")) {
                    _.extend(view.options, {
                        action_buttons: false,
                        quick_creatable: false,
                        creatable: false,
                        read_only_mode: true,
                    });
                }
            }
            views.push(view);
        });
        this.views = views;

        this.viewmanager = new X2ManyViewManager(this, this.dataset, views, this.view_options, this.x2many_views);
        this.viewmanager.x2m = self;
        var def = $.Deferred().done(function() {
            self.initial_is_loaded.resolve();
        });
        this.viewmanager.on("controller_inited", self, function(view_type, controller) {
            controller.x2m = self;
            if (view_type == "list") {
                if (self.get("effective_readonly")) {
                    controller.on('edit:before', self, function (e) {
                        e.cancel = true;
                    });
                    _(controller.columns).find(function (column) {
                        if (!(column instanceof list_widget_registry.get('field.handle'))) {
                            return false;
                        }
                        column.modifiers.invisible = true;
                        return true;
                    });
                }
            } else if (view_type == "graph") {
                self.reload_current_view();
            }
            def.resolve();
        });
        this.viewmanager.on("switch_mode", self, function(n_mode) {
            $.when(self.commit_value()).done(function() {
                if (n_mode === "list") {
                    utils.async_when().done(function() {
                        self.reload_current_view();
                    });
                }
            });
        });
        utils.async_when().done(function () {
            self.$el.addClass('o_view_manager_content');
            self.alive(self.viewmanager.attachTo(self.$el));
        });
        return def;
    },
    reload_current_view: function() {
        var self = this;
        self.is_loaded = self.is_loaded.then(function() {
            var view = self.get_active_view();
            if (view.type === "list") {
                view.controller.current_min = 1;
                return view.controller.reload_content();
            } else if (view.controller.do_search) {
                return view.controller.do_search(self.build_domain(), self.dataset.get_context(), []);
            }
        }, undefined);
        return self.is_loaded;
    },
    get_active_view: function () {
        /**
         * Returns the current active view if any.
         */
        return (this.viewmanager && this.viewmanager.active_view);
    },
    set_value: function(value_) {
        var self = this;
        this._super(value_).then(function () {
            if (self.is_started && !self.no_rerender) {
                return self.reload_current_view();
            }
        });
    },
    commit_value: function() {
        var view = this.get_active_view();
        if (view && view.type === "list" && view.controller.__focus) {
            return $.when(this.mutex.def, view.controller._on_blur_one2many());
        }
        return this.mutex.def;
    },
    is_syntax_valid: function() {
        var view = this.get_active_view();
        if (!view){
            return true;
        }
        switch (this.viewmanager.active_view.type) {
        case 'form':
            return _(view.controller.fields).chain()
                .invoke('is_valid')
                .all(_.identity)
                .value();
        case 'list':
            return view.controller.is_valid();
        }
        return true;
    },
    is_false: function() {
        return _(this.dataset.ids).isEmpty();
    },
    is_set: function() {
        // always consider that field is "set" hence displayed
        return true;
    },
});

var X2ManyDataSet = data.BufferedDataSet.extend({
    get_context: function() {
        this.context = this.x2m.build_context();
        var self = this;
        _.each(arguments, function(context) {
            self.context.add(context);
        });
        return this.context;
    },
});

var X2ManyViewManager = ViewManager.extend({
    custom_events: {
        // Catch event scrollTo to prevent scrolling to the top when using the
        // pager of List and Kanban views in One2Many fields
        'scrollTo': function() {},
    },
    init: function(parent, dataset, views, flags, x2many_views) {
        // By default, render buttons and pager in X2M fields, but no sidebar
        flags = _.extend({}, flags, {
            headless: false,
            search_view: false,
            action_buttons: true,
            pager: true,
            sidebar: false,
        });
        this.control_panel = new ControlPanel(parent, "X2ManyControlPanel");
        this.set_cp_bus(this.control_panel.get_bus());
        this._super(parent, dataset, views, flags);
        this.registry = core.view_registry.extend(x2many_views);
    },
    start: function() {
        this.control_panel.prependTo(this.$el);
        return this._super();
    },
    switch_mode: function(mode, unused) {
        if (mode !== 'form') {
            return this._super(mode, unused);
        }
        var self = this;
        var id = self.x2m.dataset.index !== null ? self.x2m.dataset.ids[self.x2m.dataset.index] : null;
        var pop = new common.FormViewDialog(this, {
            res_model: self.x2m.field.relation,
            res_id: id,
            context: self.x2m.build_context(),
            title: _t("Open: ") + self.x2m.string,
            create_function: function(data, options) {
                return self.x2m.data_create(data, options);
            },
            write_function: function(id, data, options) {
                return self.x2m.data_update(id, data, options).done(function() {
                    self.x2m.reload_current_view();
                });
            },
            alternative_form_view: self.x2m.field.views ? self.x2m.field.views.form : undefined,
            parent_view: self.x2m.view,
            child_name: self.x2m.name,
            read_function: function(ids, fields, options) {
                return self.x2m.data_read(ids, fields, options);
            },
            form_view_options: {'not_interactible_on_create':true},
            readonly: self.x2m.get("effective_readonly")
        }).open();
        pop.on("elements_selected", self, function() {
            self.x2m.reload_current_view();
        });
    },
});

var X2ManyListView = ListView.extend({
    is_valid: function () {
        if (!this.fields_view || !this.editable()){
            return true;
        }
        if (_.isEmpty(this.records.records)){
            return true;
        }
        var fields = this.editor.form.fields;
        var current_values = {};
        _.each(fields, function(field){
            field._inhibit_on_change_flag = true;
            field.__no_rerender = field.no_rerender;
            field.no_rerender = true;
            current_values[field.name] = field.get('value');
        });
        var ids = _.map(this.records.records, function (item) { return item.attributes.id; });
        var cached_records = _.filter(this.dataset.cache, function(item){return _.contains(ids, item.id) && !_.isEmpty(item.values) && !item.to_delete;});
        var valid = _.every(cached_records, function(record){
            _.each(fields, function(field){
                var value = record.values[field.name];
                field._inhibit_on_change_flag = true;
                field.no_rerender = true;
                field.set_value(_.isArray(value) && _.isArray(value[0]) ? [COMMANDS.delete_all()].concat(value) : value);
            });
            return _.every(fields, function(field){
                field.process_modifiers();
                field._check_css_flags();
                return field.is_valid();
            });
        });
        _.each(fields, function(field){
            field.set('value', current_values[field.name], {silent: true});
            field._inhibit_on_change_flag = false;
            field.no_rerender = field.__no_rerender;
        });
        return valid;
    },
    render_pager: function($node, options) {
        options = _.extend(options || {}, {
            single_page_hidden: true,
        });
        this._super($node, options);
    },
    display_nocontent_helper: function () {
        return false;
    },
});

/**
 * ListView.List subclass adding an "Add an item" row to replace the Create
 * button in the ControlPanel.
 */
var X2ManyList = ListView.List.extend({
    pad_table_to: function (count) {
        if (!this.view.is_action_enabled('create') || this.view.x2m.get('effective_readonly')) {
            this._super(count);
            return;
        }

        this._super(count > 0 ? count - 1 : 0);

        var self = this;
        var columns = _(this.columns).filter(function (column) {
            return column.invisible !== '1';
        }).length;
        if (this.options.selectable) { columns++; }
        if (this.options.deletable) { columns++; }

        var $cell = $('<td>', {
            colspan: columns,
            'class': 'o_form_field_x2many_list_row_add'
        }).append(
            $('<a>', {href: '#'}).text(_t("Add an item"))
                .click(function (e) {
                    e.preventDefault();
                    e.stopPropagation();
                    var def;
                    if (self.view.editable()) {
                        // FIXME: there should also be an API for that one
                        if (self.view.editor.form.__blur_timeout) {
                            clearTimeout(self.view.editor.form.__blur_timeout);
                            self.view.editor.form.__blur_timeout = false;
                        }
                        def = self.view.save_edition();
                    }
                    $.when(def).done(self.view.do_add_record.bind(self));
                }));

        //var $padding = this.$current.find('tr:not([data-id]):first');
        var $padding = this.$current.find('tr:first');
        var $newrow = $('<tr>').append($cell);
        if ($padding.length) {
            $padding.before($newrow);
        } else {
            this.$current.append($newrow);
        }
    },
});

var One2ManyGroups = ListView.Groups.extend({
    setup_resequence_rows: function () {
        if (!this.view.x2m.get('effective_readonly')) {
            this._super.apply(this, arguments);
        }
    }
});

var One2ManyListView = X2ManyListView.extend({
    init: function () {
        this._super.apply(this, arguments);
        this.options = _.extend(this.options, {
            GroupsType: One2ManyGroups,
            ListType: X2ManyList
        });
        this.on('edit:after', this, this.proxy('_after_edit'));
        this.on('save:before cancel:before', this, this.proxy('_before_unedit'));

        /* detect if the user try to exit the one2many widget */
        core.bus.on('click', this, this._on_click_outside);

        this.dataset.on('dataset_changed', this, function () {
            this._dataset_changed = true;
            this.dataset.x2m._dirty_flag = true;
        });
        this.dataset.x2m.on('load_record', this, function () {
            this._dataset_changed = false;
        });

        this.on('warning', this, function(e) { // In case of editable list view, we do not want any warning which comes from the editor
            if (this.editable()) {
                e.stop_propagation();
            }
        });
    },
    do_add_record: function () {
        if (this.editable()) {
            this._super.apply(this, arguments);
        } else {
            var self = this;
            new common.SelectCreateDialog(this, {
                res_model: self.x2m.field.relation,
                domain: self.x2m.build_domain(),
                context: self.x2m.build_context(),
                title: _t("Create: ") + self.x2m.string,
                initial_view: "form",
                alternative_form_view: self.x2m.field.views ? self.x2m.field.views.form : undefined,
                create_function: function(data, options) {
                    return self.x2m.data_create(data, options);
                },
                read_function: function(ids, fields, options) {
                    return self.x2m.data_read(ids, fields, options);
                },
                parent_view: self.x2m.view,
                child_name: self.x2m.name,
                form_view_options: {'not_interactible_on_create':true},
                on_selected: function() {
                    self.x2m.reload_current_view();
                }
            }).open();
        }
    },
    do_activate_record: function(index, id) {
        var self = this;
        new common.FormViewDialog(self, {
            res_model: self.x2m.field.relation,
            res_id: id,
            context: self.x2m.build_context(),
            title: _t("Open: ") + self.x2m.string,
            write_function: function(id, data, options) {
                return self.x2m.data_update(id, data, options).done(function() {
                    self.x2m.reload_current_view();
                });
            },
            create_function: function(data, options) {
                return self.x2m.data_create(data, options).done(function() {
                    self.x2m.reload_current_view();
                });
            },
            alternative_form_view: self.x2m.field.views ? self.x2m.field.views.form : undefined,
            parent_view: self.x2m.view,
            child_name: self.x2m.name,
            read_function: function(ids, fields, options) {
                return self.x2m.data_read(ids, fields, options);
            },
            form_view_options: {'not_interactible_on_create':true},
            readonly: !this.is_action_enabled('edit') || self.x2m.get("effective_readonly")
        }).open();
    },
    do_button_action: function (name, id, callback) {
        if (!_.isNumber(id)) {
            this.do_warn(_t("Action Button"),
                         _t("The o2m record must be saved before an action can be used"));
            return;
        }
        var parent_form = this.x2m.view;
        var self = this;
        this.save_edition().then(function () {
            if (parent_form) {
                return parent_form.save();
            } else {
                return $.when();
            }
        }).done(function () {
            var ds = self.x2m.dataset;
            var changed_records = _.find(ds.cache, function(record) {
                return record.to_create || record.to_delete || !_.isEmpty(record.changes);
            });
            if (!self.x2m.options.reload_on_button && !changed_records) {
                self.handle_button(name, id, callback);
            } else {
                self.handle_button(name, id, function(){
                    self.x2m.view.reload();
                });
            }
        });
    },
    start_edition: function (record, options) {
        if (!this.__focus) {
            this._on_focus_one2many();
        }
        return this._super(record, options);
    },
    reload_content: function () {
        var self = this;
        if (self.__focus) {
            self._on_blur_one2many();
            return this._super().then(function () {
                var record_being_edited = self.records.get(self.editor.form.datarecord.id);
                if (record_being_edited) {
                    self.start_edition(record_being_edited);
                }
            });
        }
        return this._super();
    },
    _on_focus_one2many: function () {
        if(!this.editor.is_editing()) {
            return;
        }
        this.dataset.x2m.internal_dataset_changed = true;
        this._dataset_changed = false;
        this.__focus = true;
    },
    _on_click_outside: function(e) {
        if(this.__ignore_blur || !this.editor.is_editing()) {
            return;
        }

        var $target = $(e.target);

        // If click on a button, a ui-autocomplete dropdown or modal-backdrop, it is not considered as a click outside
        var click_outside = ($target.closest('.ui-autocomplete,.btn,.modal-backdrop').length === 0);

        // Check if click inside the current list editable
        var $o2m = $target.closest(".o_list_editable");
        if($o2m.length && $o2m[0] === this.el) {
            click_outside = false;
        }

        // Check if click inside a modal which is on top of the current list editable
        var $modal = $target.closest(".modal");
        if($modal.length) {
            var $currentModal = this.$el.closest(".modal");
            if($currentModal.length === 0 || $currentModal[0] !== $modal[0]) {
                click_outside = false;
            }
        }

        if (click_outside) {
            this._on_blur_one2many();
        }
    },
    _on_blur_one2many: function() {
        if(this.__ignore_blur) {
            return $.when();
        }

        this.__ignore_blur = true;
        this.__focus = false;
        this.dataset.x2m.internal_dataset_changed = false;

        var self = this;
        return this.save_edition(true).done(function () {
            if (self._dataset_changed) {
                self.dataset.trigger('dataset_changed');
            }
        }).always(function() {
            self.__ignore_blur = false;
        });
    },
    _after_edit: function () {
        this.editor.form.on('blurred', this, this._on_blur_one2many);

        // The form's blur thing may be jiggered during the edition setup,
        // potentially leading to the x2m instasaving the row. Cancel any
        // blurring triggered the edition startup here
        this.editor.form.widgetFocused();
    },
    _before_unedit: function () {
        this.editor.form.off('blurred', this, this._on_blur_one2many);
    },
    do_delete: function (ids) {
        var confirm = window.confirm;
        window.confirm = function () { return true; };
        try {
            return this._super(ids);
        } finally {
            window.confirm = confirm;
        }
    },
    reload_record: function (record, options) {
        if (!options || !options.do_not_evict) {
            // Evict record.id from cache to ensure it will be reloaded correctly
            this.dataset.evict_record(record.get('id'));
        }

        return this._super(record);
    },
});

var FieldOne2ManyEditOnTop = FieldX2Many.extend({
    init: function() {
        this._super.apply(this, arguments);
        this.x2many_views = {
            kanban: core.view_registry.get('one2many_kanban'),
            list: One2ManyListView,
        };
    },
    start: function() {
        this.$el.addClass('o_form_field_one2many');
        return this._super.apply(this, arguments);
    },
    commit_value: function() {
        var self = this;
        return this.is_loaded.then(function() {
            var view = self.viewmanager.active_view;
            if(view.type === "list" && view.controller.editable()) {
                return self.mutex.def.then(function () {
                    return view.controller.save_edition();
                });
            }
            return self.mutex.def;
        });
    },
    is_false: function() {
        return false;
    },
});

var Many2ManyListView = X2ManyListView.extend({
    init: function () {
        this._super.apply(this, arguments);
        this.options = _.extend(this.options, {
            ListType: X2ManyList,
        });
        this.on('edit:after', this, this.proxy('_after_edit'));
        this.on('save:before cancel:before', this, this.proxy('_before_unedit'));
    },
    do_add_record: function () {
        var self = this;

        new common.SelectCreateDialog(this, {
            res_model: this.model,
            domain: new data.CompoundDomain(this.x2m.build_domain(), ["!", ["id", "in", this.x2m.dataset.ids]]),
            context: this.x2m.build_context(),
            title: _t("Add: ") + this.x2m.string,
            alternative_form_view: this.x2m.field.views ? this.x2m.field.views.form : undefined,
            no_create: this.x2m.options.no_create || !this.is_action_enabled('create'),
            on_selected: function(element_ids) {
                return self.x2m.data_link_multi(element_ids).then(function() {
                    self.x2m.reload_current_view();
                });
            }
        }).open();
    },
    do_activate_record: function(index, id) {
        var self = this;
        var pop = new common.FormViewDialog(this, {
            res_model: this.model,
            res_id: id,
            context: this.x2m.build_context(),
            title: _t("Open: ") + this.x2m.string,
            alternative_form_view: this.x2m.field.views ? this.x2m.field.views.form : undefined,
            readonly: !this.is_action_enabled('edit') || self.x2m.get("effective_readonly"),
        }).open();
        pop.on('write_completed', self, function () {
            self.dataset.evict_record(id);
            self.reload_content();
        });
    },
    do_button_action: function(name, id, callback) {
        var self = this;
        var _sup = _.bind(this._super, this);
        if (! this.x2m.options.reload_on_button) {
            return _sup(name, id, callback);
        } else {
            return this.x2m.view.save().then(function() {
                return _sup(name, id, function() {
                    self.x2m.view.reload();
                });
            });
        }
    },
    _after_edit: function () {
        this.editor.form.on('blurred', this, this._on_blur_many2many);
    },
    _before_unedit: function () {
        this.editor.form.off('blurred', this, this._on_blur_many2many);
    },
    _on_blur_many2many: function() {
        return this.save_edition().done(function () {
            if (self._dataset_changed) {
                self.dataset.trigger('dataset_changed');
            }
        });
    },

});

var FieldMany2ManyEditOnTop = FieldX2Many.extend({
    init: function() {
        this._super.apply(this, arguments);
        this.x2many_views = {
            list: Many2ManyListView,
            kanban: core.view_registry.get('many2many_kanban'),
        };
    },
    start: function() {
        this.$el.addClass('o_form_field_many2many');
        return this._super.apply(this, arguments);
    }
});

core.form_widget_registry
    .add('one2many_edit_on_top', FieldOne2ManyEditOnTop)
    .add('many2many_edit_on_top', FieldMany2ManyEditOnTop)

return {
    FieldMany2ManyEditOnTop: FieldMany2ManyEditOnTop,
};

});
