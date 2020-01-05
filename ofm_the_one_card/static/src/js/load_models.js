odoo.define('ofm_the_one_card.load_models', function (require) {
    "use strict";

    var PosBaseWidget = require('point_of_sale.BaseWidget');
    var models = require('point_of_sale.models');
    var PosDB = require('point_of_sale.DB');

    var gui = require('point_of_sale.gui');
    var screens = require('point_of_sale.screens');
    var core = require('web.core');
    var popups = require('point_of_sale.popups');
    var QWeb = core.qweb;
    var _t = core._t;
    var Model = require('web.DataModel');

    models.load_models([{
        label:  'The One Parameter',
        loaded: function(self, parameters){
            return new Model('tr.call.api').call('get_the_one_card_api').then(function(result){
                self.the_1_config = result;
            });
        },
        },
        {
            label:  'cors proxy (from config)',
            loaded: function(self, parameters){
                return new Model('pos.order').call('get_cors_proxy').then(function(result){
                    self.cors_proxy = "http://" + result + "/";
                });
            },
        }
        ]);

    models.load_models([{
        model: 'point.template',
        fields: [],
        loaded: function(self, templates){
            self.point_templates_by_id = {};
            $.each(templates, function(idx, temp){
                const current_branch_id = self.branch.id;
                const template_branch_ids = temp.branch_ids;
                const is_relevant = template_branch_ids.includes(current_branch_id);
                if (is_relevant) {
                    self.point_templates_by_id[temp.id] = temp;
                    self.point_templates_by_id[temp.id].point_template_line_ids = [];
                }
            })
        },
    }]);

    models.load_models([{
        model: 'point.template.line',
        fields: [],
        loaded: function(self, template_lines){
            $.each(template_lines, function(idx, temp_line){
                const point_template_id = temp_line.point_template_id[0];
                var template = self.point_templates_by_id[point_template_id]
                if (template){
                    template.point_template_line_ids.push(temp_line);
                }
            })
        },
    }]);

    //allowing all fields for account journal for checking flags
    models.load_models([{
        model:  'account.journal',
        fields: [],
        domain: function(self,tmp){ return [['id','in',tmp.journals]]; },
        loaded: function(self, journals){
            var i;
            self.journals = journals;

            // associate the bank statements with their journals. 
            var cashregisters = self.cashregisters;
            var ilen = cashregisters.length;
            for(i = 0; i < ilen; i++){
                for(var j = 0, jlen = journals.length; j < jlen; j++){
                    if(cashregisters[i].journal_id[0] === journals[j].id){
                        cashregisters[i].journal = journals[j];
                    }
                }
            }

            self.cashregisters_by_id = {};
            for (i = 0; i < self.cashregisters.length; i++) {
                self.cashregisters_by_id[self.cashregisters[i].id] = self.cashregisters[i];
            }

            self.cashregisters = self.cashregisters.sort(function(a,b){ 
                // prefer cashregisters to be first in the list
                if (a.journal.type == "cash" && b.journal.type != "cash") {
                    return -1;
                } else if (a.journal.type != "cash" && b.journal.type == "cash") {
                    return 1;
                } else {
                            return a.journal.sequence - b.journal.sequence;
                }
            });

        },
    }]);

    models.load_models([{
        model: 'redeem.type',
        fields: [],
        loaded: function(self, redeem_types){
            self.redeem_types_by_id = {};
            $.each(redeem_types, function(idx, type){
                self.redeem_types_by_id[type.id] = type;
            }); 
            
            $.each(self.cashregisters, function(idx, cashregister){
                if (cashregister.journal.redeem_type_id) {
                    let redeem_type = self.redeem_types_by_id[cashregister.journal.redeem_type_id[0]];
                    cashregister.journal.redeem_type_id = redeem_type;
                }
            });
        },
    }]);

    PosDB.include({
        pos_order_fields: function(){
            return this._super().concat(['the_one_card_no', 'company', 'status', 'tier', 'lines', 'cg_staff', 'balance_points'
            , 'redeem_rights' ,'segment', 'staff', 'expire_this_year', 'pos_offline', 't1c_set', 'membercard', 'phone_number'
            , 'points_expiry_this_year', 'points_balance', 'member_name', 'membercard']);
        },
    });

});