odoo.define('pos_customer_information.list_thai_address_information', function (require) {
    "use strict";
    var screens = require('point_of_sale.screens');
    var models = require('point_of_sale.models');
    var PosDB = require('point_of_sale.DB');
    var Model = require('web.DataModel');

    PosDB.include({
        init: function (options) {
            this._super(options);
            this.province_by_id = {};
            this.amphur_by_id = {};
            this.tambon_by_id = {};
            this.postcode_by_name = {};

            this.province = [];
            this.amphur = [];
            this.tambon = [];
            this.postcode = [];
        },
    });

    models.load_models([
        {
            label: 'Loading cache address',
            loaded: function (self) {
                return new Model('res.partner').call('get_address_cache').then(function(datas){
                    datas.forEach(function(data){
                        data.datas.forEach(function(item, index){
                            item.index = index;
                            self.db[data.name].push(item);
                            if(data.name == 'postcode')
                                self.db[data.name + '_by_name'][item.name] = item;
                            else
                                self.db[data.name + '_by_id'][item.id] = item;
                        });
                    });
                });
            }
        }
    ], {'before': 'res.partner'});


    screens.ClientListScreenWidget.include({
        init: function(parent, options){
            var self = this;
            this._super(parent, options);

            this.province_by_id = this.pos.db.province_by_id;
            this.amphur_by_id = this.pos.db.amphur_by_id;
            this.tambon_by_id = this.pos.db.tambon_by_id;
            this.postcode_by_name = this.pos.db.postcode_by_name;

            this.province = this.pos.db.province;
            this.amphur = this.pos.db.amphur;
            this.tambon = this.pos.db.tambon;
            this.postcode = this.pos.db.postcode;
        },

        //list of province, amphur, tambon is sorted by alphabet
        get_province_by_name: function(name){
            for(var idx = 0; idx < this.province.length; idx++){
                if(name.toString().localeCompare(this.province[idx].name.toString(), 'th') == 0){
                    return this.province[idx];
                }
            }
            return false;
        },
        get_amphur_by_name: function(name){
            for(var idx = 0; idx < this.amphur.length; idx++){
                if(name.toString().localeCompare(this.amphur[idx].name.toString(), 'th') == 0){
                    return this.amphur[idx];
                }
            }
            return false;
        },
        get_tambon_by_name: function(name){
            for(var idx = 0; idx < this.tambon.length; idx++){
                if(name.toString().localeCompare(this.tambon[idx].name.toString(), 'th') == 0){
                    return this.tambon[idx];
                }
            }
            return false;
        },
    });
});