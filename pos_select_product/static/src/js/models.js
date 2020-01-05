odoo.define('pos_select_product.models', function (require) {
    "use strict";

    var BarcodeParser = require('barcodes.BarcodeParser');
    var PosDB = require('point_of_sale.DB');
    var devices = require('point_of_sale.devices');
    var core = require('web.core');
    var Model = require('web.DataModel');
    var formats = require('web.formats');
    var session = require('web.session');
    var time = require('web.time');
    var utils = require('web.utils');
    var models = require('point_of_sale.models');


    var QWeb = core.qweb;
    var _t = core._t;
    var Mutex = utils.Mutex;
    var round_di = utils.round_decimals;
    var round_pr = utils.round_precision;
    var Backbone = window.Backbone;

    var exports = models;

    //pos_product_template_line_ids

//    models.load_fields('pos.config', ['pos_product_template_line_ids']);

    PosDB.include({
        init: function (options) {
            this._super(options);
            this.template_product_ids = [];
//            this.product_by_id = {};
//            this.product_by_barcode = {};
//            this.product_by_category_id = {};
            this.product_by_brand_id = {};
            this.product_by_categ_id = {};
            this.product_by_dept_id = {};

            this.product_categ_ids = [];
            this.product_brand_ids = [];
            this.product_dept_ids = [];
        },
        add_products: function (products) {
            var stored_categories = this.product_by_category_id;

            if(!products instanceof Array){
                products = [products];
            }
            for(var i = 0, len = products.length; i < len; i++){
                var product = products[i];
                var search_string = this._product_search_string(product);
                var categ_id = product.pos_categ_id ? product.pos_categ_id[0] : this.root_category_id;
                product.product_tmpl_id = product.product_tmpl_id[0];
                if(!stored_categories[categ_id]){
                    stored_categories[categ_id] = [];
                }
                stored_categories[categ_id].push(product.id);

                if(this.category_search_string[categ_id] === undefined){
                    this.category_search_string[categ_id] = '';
                }
                this.category_search_string[categ_id] += search_string;

                var ancestors = this.get_category_ancestors_ids(categ_id) || [];

                for(var j = 0, jlen = ancestors.length; j < jlen; j++){
                    var ancestor = ancestors[j];
                    if(! stored_categories[ancestor]){
                        stored_categories[ancestor] = [];
                    }
                    stored_categories[ancestor].push(product.id);

                    if( this.category_search_string[ancestor] === undefined){
                        this.category_search_string[ancestor] = '';
                    }
                    this.category_search_string[ancestor] += search_string;
                }


                var categ_id = product.categ_id ? product.categ_id : [0, "None"];
                if(categ_id[0] in this.product_by_categ_id){
                    this.product_by_categ_id[categ_id[0]].product_ids.push(product.id);
                }
                else{
                    this.product_categ_ids.push(categ_id[0]);
                    this.product_by_categ_id[categ_id[0]] = {
                        id: categ_id[0],
                        name: categ_id[1],
                        product_ids: [product.id],
                    }
                }

                var brand_id = product.brand_id ? product.brand_id : [0, "None"];
                if(brand_id[0] in this.product_by_brand_id){
                    this.product_by_brand_id[brand_id[0]].product_ids.push(product.id);
                }
                else{
                    this.product_brand_ids.push(brand_id[0]);
                    this.product_by_brand_id[brand_id[0]] = {
                        id: brand_id[0],
                        name: brand_id[1],
                        product_ids: [product.id],
                    }
                }

                var dept_id = product.dept_ofm ? product.dept_ofm : [0, "None"];
                if(dept_id[0] in this.product_by_dept_id){
                    this.product_by_dept_id[dept_id[0]].product_ids.push(product.id);
                }
                else{
                    this.product_dept_ids.push(dept_id[0]);
                    this.product_by_dept_id[dept_id[0]] = {
                        id: dept_id[0],
                        name: dept_id[1],
                        product_ids: [product.id],
                    }
                }
                var dept = this.dept_by_id[dept_id[0]]
                if(dept && dept.dept_parent_id){
                    if(dept.dept_parent_id[0] in this.product_by_dept_id){
                        this.product_by_dept_id[dept.dept_parent_id[0]].product_ids.push(product.id);
                    }
                    else{
                        this.product_dept_ids.push(dept.dept_parent_id[0]);
                        this.product_by_dept_id[dept.dept_parent_id[0]] = {
                            id: dept.dept_parent_id[0],
                            name: dept.dept_parent_id[1],
                            product_ids: [product.id],
                        }
                    }
                }

                this.product_by_id[product.id] = product;
                if(product.barcode){
                    this.product_by_barcode[product.barcode] = product;
                }
                if(product.default_code && product.display_name.indexOf(product.default_code) == '-1')
                    product.display_name += ' (' + product.default_code +')';
            }

        },
        get_product_by_categ: function (categ_id) {
            var product_ids = this.product_by_categ_id[categ_id].product_ids;
            var list = [];
            if (product_ids) {
                for (var i = 0; i < product_ids.length; i++) {
                    if (this.product_by_id[product_ids[i]]) {
                        list.push(this.product_by_id[product_ids[i]]);
                    }
                }
            }
            return list;
        },
    });


    models.load_models = function (models, options) {
        options = options || {};
        if (!(models instanceof Array)) {
            models = [models];
        }

        var pmodels = exports.PosModel.prototype.models;
        var index = pmodels.length;

        if (options.replace) {
            for (var i = 0; i < pmodels.length; i++) {
                if (pmodels[i].model === options.replace ||
                        pmodels[i].label === options.replace) {
                    index = i;
                }
            }
            // replace but keep load_fields of old model working
            models[0].fields = _.uniq($.merge(pmodels[index].fields, models[0].fields));
            pmodels[index] = models[0];
        } else {
            if (options.before) {
                for (var i = 0; i < pmodels.length; i++) {
                    if (pmodels[i].model === options.before ||
                            pmodels[i].label === options.before) {
                        index = i;
                        break;
                    }
                }
            } else if (options.after) {
                for (var i = 0; i < pmodels.length; i++) {
                    if (pmodels[i].model === options.after ||
                            pmodels[i].label === options.after) {
                        index = i + 1;
                    }
                }
            }

            pmodels.splice.apply(pmodels, [index, 0].concat(models));
        }

    };

    models.load_models([
        {
            model: 'pos.product.template.line',
            fields: ['product_id_int'],
            domain: function (self) {
                return [['template_id', '=', self.config.pos_product_template_id[0]]];
            },
            loaded: function (self, template_lines) {

                var temp = [];
                $.each(template_lines, function(id, value){
                    temp.push(value['product_id_int']);
                });

                if(self.config.promotion_discount_product_id){
                    temp.push(self.config.promotion_discount_product_id[0]);
                }
                if(self.config.vip_discount_product_id){
                     temp.push(self.config.vip_discount_product_id[0]);
                }

                if(self.db.template_product_ids instanceof Array)
                    self.db.template_product_ids = self.template_product_ids = _.union(self.db.template_product_ids, temp);
                else
                    self.db.template_product_ids = self.template_product_ids = temp;
            }
        }
    ], {'after': 'pos.category'});

    models.load_models([
        {
            model: 'product.uom',
            fields: [],
            domain: null,
            context: function (self) {
                return {active_test: false};
            },
            loaded: function (self, units) {
                self.units = units;
                var units_by_id = {};
                for (var i = 0, len = units.length; i < len; i++) {
                    units_by_id[units[i].id] = units[i];
                    units[i].groupable = true;
                    units[i].is_unit = true;
                }
                self.units_by_id = units_by_id;
            }
        }
    ], {'replace': 'product.uom'});

    models.load_models([
        {
            model: 'ofm.product.dept',
            fields: [],
            domain: null,
            loaded: function (self, departments) {
                self.db.dept_by_id = {};
                departments.forEach(function(department){
                    self.db.dept_by_id[department.id] = department;
                });
            }
        }
    ], {'before': 'product.product'});

    models.load_models([
        {
            model: 'product.product',
            fields: ['id', 'name', 'type', 'display_name', 'list_price', 'price', 'pos_categ_id', 'taxes_id', 'barcode', 'default_code',
                'to_weight', 'uom_id', 'description_sale', 'description',
                'product_tmpl_id', 'is_pack', 'product_pack_id', 'lst_price',
                'brand_id', 'dept_ofm', 'categ_id', 'tracking',
                ],
            order: ['sequence', 'default_code', 'name'],
            domain: function (self) {
                return [['sale_ok', '=', true], ['available_in_pos', '=', true], ['id', 'in', self.db.template_product_ids]];
            },
            context: function (self) {
                return {pricelist: self.pricelist.id, display_default_code: false, pricelist_branch_id: self.config.branch_id[0]};
            },
            loaded: function (self, products) {
                var products_pack = [];
                self.db.products = products;
                self.db.add_products(products);
                $.each(products, function (i, product) {
                    if (product.is_pack) {
                        products_pack.push(product);
                    }
                });
                self.set({'product_pack': products_pack});
            },
        }
    ], {'replace': 'product.product'});

});