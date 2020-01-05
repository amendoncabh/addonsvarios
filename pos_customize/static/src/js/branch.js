odoo.define('pos_customize.branch', function (require) {
    "use strict";

    var gui = require('point_of_sale.gui');
    var models = require('point_of_sale.models');
    var PosDB = require('point_of_sale.DB');
    var screens = require('point_of_sale.screens');
    var popups = require('point_of_sale.popups');
    var core = require('web.core');
    var _t = core._t;
    var QWeb = core.qweb;



    models.load_models([
        {
            model: 'pos.branch',
            domain: [],
            fields: ['branch_name', 'branch_id', 'street', 'street2', 'zip', 'city', 'state_id', 'country_id',
                    'email', 'phone', 'promotion_ids', 'manager_user_ids', 'branch_code'],
            loaded: function (self, branches) {
                self.db.branch_by_id = {};
                branches.forEach(function(branch){
                    self.db.branch_by_id[branch.id] = branch;
                });
                if (self.config.branch_id[0] in self.db.branch_by_id) {
                    self.branch = self.db.branch_by_id[self.config.branch_id[0]];
                }
                else{
                    self.branch = null;
                }
            },
        }
    ], {'before': 'product.product'});


});

