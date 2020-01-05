/* © <YEAR(S)> <AUTHOR(S)>
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
 */
odoo.define('ofm_custom_search_in_field.form_relational', function (require) {
    var form_common = require('web.form_common');
    var form_relational = require('web.form_relational');
    var data = require('web.data');
    var core = require('web.core');

    var QWeb = core.qweb;
    var _t = core._t;

    form_relational.FieldMany2One.include({
        get_search_result: function(search_val) {
            var self = this;

            var dataset = new data.DataSet(this, this.field.relation, self.build_context());
            this.last_query = search_val;
            var exclusion_domain = [], ids_blacklist = this.get_search_blacklist();
            if (!_(ids_blacklist).isEmpty()) {
                exclusion_domain.push(['id', 'not in', ids_blacklist]);
            }

            return this.orderer.add(dataset.name_search(
                    search_val, new data.CompoundDomain(self.build_domain(), exclusion_domain),
                    'ilike', this.limit + 1, self.build_context())).then(function(_data) {
                self.last_search = _data;
                // possible selections for the m2o
                var values = _.map(_data, function(x) {
                    x[1] = x[1].split("\n")[0];
                    return {
                        label: _.str.escapeHTML(x[1].trim()) || data.noDisplayContent,
                        value: x[1],
                        name: x[1],
                        id: x[0],
                    };
                });

                // search more... if more results that max
                if (values.length > self.limit) {
                    values = values.slice(0, self.limit);
                    values.push({
                        label: _t("Search More..."),
                        action: function() {
                            dataset.name_search(search_val, self.build_domain(), 'ilike', 100).done(function(_data) {
                                self._search_create_popup("search", _data);
                            });
                        },
                        classname: 'o_m2o_dropdown_option'
                    });
                }
                // quick create
                var raw_result = _(_data.result).map(function(x) {return x[1];});
                if (search_val.length > 0 && !_.include(raw_result, search_val) &&
                    ! (self.options && (self.options.no_create || self.options.no_quick_create))) {
                    self.can_create && values.push({
                        label: _.str.sprintf(_t('Create "<strong>%s</strong>"'),
                            $('<span />').text(search_val).html()),
                        action: function() {
                            self._quick_create(search_val);
                        },
                        classname: 'o_m2o_dropdown_option'
                    });
                }
                // create...
                if (!(self.options && (self.options.no_create || self.options.no_create_edit)) && self.can_create){
                    values.push({
                        label: _t("Create and Edit..."),
                        action: function() {
                            self._search_create_popup("form", undefined, self._create_context(search_val));
                        },
                        classname: 'o_m2o_dropdown_option'
                    });
                }
                else if (values.length === 0) {
                    values.push({
                        label: _t("No results to show..."),
                        action: function() {},
                        classname: 'o_m2o_dropdown_option'
                    });
                }

                return values;
            });
        },
    });

//    form_relational.CompletionFieldMixin = form_common.CompletionFieldMixin.extend({
//
//    });
});


