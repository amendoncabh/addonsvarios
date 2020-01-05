odoo.define('ofm_promotion.promotion_view', function (require) {
    "use strict";

    var core = require('web.core');
    var session = require('web.session');
    var Model = require('web.DataModel');
    var utils = require('web.utils');
    var gui = require('point_of_sale.gui');
    var models = require('point_of_sale.models');
    var PosDB = require('point_of_sale.DB');
    var screens = require('point_of_sale.screens');
    var popups = require('point_of_sale.popups');

    var round_pr = utils.round_precision;

    var _t = core._t;
    var QWeb = core.qweb;

    PosDB.include({
        pos_order_fields: function(){
            return this._super().concat([]);
        },
        pos_order_line_fields: function(){
            return this._super().concat(['promotion', 'promotion_id', 'promotion_condition_id'
            , 'promotion_type', 'reward_type', 'promotion_name', 'prorate_amount', 'prorate_amount_exclude'
            , 'prorate_vat', 'free_product_id', 'line_coupon', 'multi_coupon_id', 'multi_coupon_barcode']);
        },
        get_barcode_image: function(barcode){
            var canvas = document.createElement("canvas");
            JsBarcode(canvas, barcode, {
                format: "CODE128",
                weight: 600,
                height: 70,
                displayValue: false,
            });
            return canvas.toDataURL("image/png");
        },
        get_product_images: function(product_ids){
            return new Model('product.product').call('load_product_images', [{
                'product_ids': product_ids,
            }]).done(function(result){
                return result;
            });
        },
        add_products: function (products) {
            var self = this;
            var load_images_coupon_ids = [];
            products.forEach(function(product){
                if(product.is_coupon){
                    // force price to zero
                    product.price = product.lst_price = product.list_price = 0;
                    // load image coupon
                    if(product.coupon_type == 'single'){
                        product.coupon_barcode_image_base64 = self.get_barcode_image(product.barcode);
                    }
                    else if(product.coupon_type == 'multi'){
                        product.hide_in_pos_product_list = true;
                    }
                    load_images_coupon_ids.push(product.id);
                }
            });

            self.get_product_images(load_images_coupon_ids).then(function(result){
                if(result.status == 'success'){
                    load_images_coupon_ids.forEach(function(product_id){
                        if(product_id in result && result[product_id])
                            self.product_by_id[product_id].image_base64 = 'data:image/png;base64,' + result[product_id];
                    });
                }
            })

            this._super(products);
        },
        add_promotions: function(promotions){
            if(!promotions instanceof Array)
                promotions = [promotions];
            var self = this;
            promotions.forEach(function (promotion){
                promotion.condition_ids = [];
                promotion.tier = parseInt(promotion.tier);
                promotion.priority = parseInt(promotion.priority) - 1; // make to array index
                self.promotion_by_id[promotion.id] = promotion;
            });
        },
        add_promotion_conditions: function(conditions){
            if(!conditions instanceof Array)
                conditions = [conditions];
            var self = this;
            conditions.forEach(function(condition){
                if(!(condition.promotion_id[0] in self.promotion_by_id))
                    return;

                condition.condition_apply_id = 0;
                if(condition.condition_product == 'brand')
                    condition.condition_apply_id = condition.condition_brand_id[0];
                else if (condition.condition_product == 'category')
                    condition.condition_apply_id = condition.condition_categ_id[0];
                else if (condition.condition_product == 'dept')
                    condition.condition_apply_id = condition.condition_dept[0];
                else if (condition.condition_product == 'sub_dept')
                    condition.condition_apply_id = condition.condition_sub_dept[0];

                condition.reward_apply_id = 0;
                if(condition.reward_product == 'brand')
                    condition.reward_apply_id = condition.reward_brand_id[0];
                else if (condition.reward_product == 'category')
                    condition.reward_apply_id = condition.reward_categ_id[0];
                else if (condition.reward_product == 'dept')
                    condition.reward_apply_id = condition.reward_dept[0];
                else if (condition.reward_product == 'sub_dept')
                    condition.reward_apply_id = condition.reward_sub_dept[0];

                condition.exclude_condition_apply_id = 0;
                if(condition.exclude_condition_product == 'brand')
                    condition.exclude_condition_apply_id = condition.exclude_condition_brand_id[0];
                else if (condition.exclude_condition_product == 'category')
                    condition.exclude_condition_apply_id = condition.exclude_condition_categ_id[0];
                else if (condition.exclude_condition_product == 'dept')
                    condition.exclude_condition_apply_id = condition.exclude_condition_dept[0];
                else if (condition.exclude_condition_product == 'sub_dept')
                    condition.exclude_condition_apply_id = condition.exclude_condition_sub_dept[0];

                condition.exclude_reward_apply_id = 0;
                if(condition.exclude_reward_product == 'brand')
                    condition.exclude_reward_apply_id = condition.exclude_reward_brand_id[0];
                else if (condition.exclude_reward_product == 'category')
                    condition.exclude_reward_apply_id = condition.exclude_reward_categ_id[0];
                else if (condition.exclude_reward_product == 'dept')
                    condition.exclude_reward_apply_id = condition.exclude_reward_dept[0];
                else if (condition.exclude_reward_product == 'sub_dept')
                    condition.exclude_reward_apply_id = condition.exclude_reward_sub_dept[0];

                condition.condition_manual_product = [];
                condition.condition_mapping_product_qty_ids = [];
                condition.reward_manual_product = [];
                condition.reward_mapping_product_qty_ids = [];

                self.promotion_by_id[condition.promotion_id[0]].condition_ids.push(condition);
                self.promotion_condition_by_id[condition.id] = condition;
            });
        },
        add_promotion_condition_product_qty: function(product_qty_ids){
            if(!product_qty_ids instanceof Array)
                product_qty_ids = [product_qty_ids];
            var self = this;
            var load_product_reward = []
            var reward_product_ids = []
            product_qty_ids.forEach(function(product_qty_id){
                var condition_id = product_qty_id.promotion_condition_id[0]
                if(!(condition_id in self.promotion_condition_by_id))
                    return;
                if(product_qty_id.model_type === 'reward'){
                    var reward_product_id = product_qty_id.product_id_int;
                    self.promotion_condition_by_id[condition_id].reward_mapping_product_qty_ids.push(product_qty_id);
                    // prepare list of old manual product
                    self.promotion_condition_by_id[condition_id].reward_manual_product.push(reward_product_id);

                    if(!reward_product_ids.includes(reward_product_id))
                        reward_product_ids.push(reward_product_id);
                    if(!load_product_reward.includes(reward_product_id))
                        load_product_reward.push(reward_product_id);
                }
                else /*if(model_type === 'condition')*/{
                    self.promotion_condition_by_id[condition_id].condition_mapping_product_qty_ids.push(product_qty_id);
                    // prepare list of old manual product
                    self.promotion_condition_by_id[condition_id].condition_manual_product.push(product_qty_id.product_id_int);
                }
                self.promotion_condition_product_qty_by_id[product_qty_id.id] = product_qty_id;
            });
            self.reward_product_ids = reward_product_ids;
            self.load_product_reward = load_product_reward;
            self.template_product_ids = _.union(self.template_product_ids, load_product_reward);
        },
        coupon_api: function(param, options={}){
            var message_err = [];
            if(!('process_type' in param))
                message_err.push('no process_type')
            if(!('product_ids' in param))
                message_err.push('no product_ids')

            if(message_err.length){
                console.err(message_err.join())
                return false;
            }
            return new Model('product.product').call('coupon_process', [param], {}, options).done(function(result){
                return result;
            });
        },
        get_barcode_coupon: function(product_ids){
            return this.coupon_api({
                'process_type': 'receive',
                'product_ids': product_ids,
            });
        },
        inquiry_coupon: async function(product, coupon, barcode){
            var self = this;
            posmodel.chrome.loading_show();
            posmodel.chrome.loading_message('กรุณารอสักครู่ ระบบตรวจสอบคูปอง', 0.5);

            var result = await this.coupon_api({
                'multi_coupon_id': coupon.id,
                'process_type': 'reserve',
                'product_ids': [product.id],
                'barcode': barcode,
            }).always(function(){
                posmodel.chrome.loading_hide();
            });

            if(result.status == 'success'){
                var coupon_product = _.recursiveDeepCopy(product);
                var multi_coupon_id = this.multi_coupon_by_barcode[barcode].id;
                var order = posmodel.get_order();
                //set order to temporary
                order.temporary = true;

                //add coupon
                order.add_product(
                    coupon_product, {
                        price: 0,
                        multi_line: true,
                        extras: {
                            multi_coupon_id: multi_coupon_id,
                            coupon_barcode: barcode,
                        }
                    }
                );
                var orderline = posmodel.get_order().get_orderlines().find(function(line){
                    return (line.multi_coupon_id == multi_coupon_id && line.coupon_barcode == barcode);
                });
                if(order && orderline){
                    orderline.remove_timeout = setTimeout(function(){
                        if(orderline){
                            self.unreserved_reserve_coupon(coupon_product.id, barcode);
                            order.remove_orderline(orderline);
                            if(!order.has_multi_coupon_with_barcode()){
                                //cannot find, then unset order to temporary
                                order.temporary = false;
                            }
                        }
                    }, posmodel.multi_coupon_unreserved_time * 60000);
                }
                return barcode;
            }
            else if(result.status == 'fail'){
                posmodel.gui.show_popup('alert', {
                    'title': _t('Alert Coupon'),
                    'body': result.message,
                });
                return false;
            }
            else{
                console.err(result);
                return false;
            }
        },
        unreserved_reserve_coupon: async function(product_id, barcode){
            posmodel.chrome.loading_show();
            posmodel.chrome.loading_message('กรุณารอสักครู่ ระบบตรวจสอบคูปอง', 0.5);

            var result = await this.coupon_api({
                'process_type': 'unreserved',
                'product_ids': [product_id],
                'barcode': barcode,
            }).always(function(){
                posmodel.chrome.loading_hide();
            });

            if(result.status == 'success'){
                return result;
            }
            else if(result.status == 'fail'){
                posmodel.gui.show_popup('alert', {
                    'title': _t('Alert Coupon'),
                    'body': result.message,
                });
                return false;
            }
            else{
                console.err(result);
                return false;
            }
        },
        search_product_in_category: function(category_id, query){
            var self = this;
            if(query in this.multi_coupon_by_barcode){
                var coupon = this.multi_coupon_by_barcode[query];
                var product = this.product_by_id[coupon.product_id[0]];
                if(product){
                    this.inquiry_coupon(product, coupon, query);
                    posmodel.gui.current_screen.product_categories_widget.clear_search();
                    return this._super(category_id, '');
                }
            }
            var products = this._super(category_id, query);
            // filter out multi coupon
            products = products.filter((product)=> !self.coupon_multi_ids.includes(product.id));
            return products;
        },
        multi_coupon_validation: async function(is_shadow = false){
            var keys = _.keys(this.condition_by_rewrd_coupon_multi_id);
            if(keys.length){
                var self = this;
                var options = undefined;
                if(is_shadow)
                    options = {timeout: 3000};
                else{
                    posmodel.chrome.loading_show();
                    posmodel.chrome.loading_message(_t('กำลังตรวจสอบโปรโมชั่น'), 0.6);
                }
                var result = await this.coupon_api({
                    'process_type': 'check_multi_coupon',
                    'product_ids': keys,
                }, options).then(function(result){
                    return result;
                }).always(function(){
                    !is_shadow && posmodel.chrome.loading_hide();
                });

                var to_inactive_promotion = [];
                var to_remove_coupon = [];
                keys.forEach(function(product_id){
                    if(!(product_id in result && result[product_id] > 0)){
                        self.condition_by_rewrd_coupon_multi_id[product_id].forEach(function(condition){
                            condition.inactive = true;
                            to_inactive_promotion.push(condition.promotion_id[0]);
                        });
                        to_remove_coupon.push(product_id);
                    }
                });
                if(to_inactive_promotion.length){
                    _.unique(to_inactive_promotion).forEach(function(promotion_id){
                        var promotion = self.promotion_by_id[promotion_id];
                        if(promotion && !promotion.condition_ids.find((condition)=>!condition.inactive)){
                            // cannot find the active condition, then inactive to the promotion
                            promotion.active = false;
                        }
                    })
                }
                if(to_remove_coupon.length){
                    to_remove_coupon.forEach(function(product_id){
                        delete self.condition_by_rewrd_coupon_multi_id[product_id];
                    });
                }
                return to_inactive_promotion;
            }
            else{
                return false;
            }
        },
    });

    models.load_fields('product.product', ['is_coupon', 'is_coupon_confirm', 'coupon_type', 'multi_coupon_ids']);

    models.load_models([{
        model:  'ir.config_parameter',
        fields: ['key','value'],
        domain: function(self){ return [['key','in', ['pos_promotion', 'pos_promotion_threshold', 'multi_coupon_unreserved_time']]]; },
        limit: 1,
        loaded: function(self, parameters){
            parameters.forEach(function(parameter){
                if(parameter.key === 'pos_promotion')
                    self.system_parameter_pos_promotion = (parameter.value == 'True')?true: false;
                else if(parameter.key === 'pos_promotion_threshold'){
                    if(!_.isNumber(parameter.value))
                        parameter.value = parseFloat(parameter.value);
                    self.system_parameter_pos_promotion_threshold = parameter.value/100;
                }
                else if(parameter.key === 'multi_coupon_unreserved_time'){
                    if(!_.isNumber(parameter.value))
                        parameter.value = parseFloat(parameter.value);
                    self.multi_coupon_unreserved_time = parameter.value;
                }
            });
        },
    },{
        model:  'account.journal',
        fields: ['type', 'sequence', 'flag_change', 'is_credit_card'],
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
                return a.journal.sequence - b.journal.sequence;
            });

        },
    },]);

    models.load_models([{
        model:  'pos.promotion.tier',
        domain: [],
        fields: ['id', 'name', 'start_tier', 'end_tier', 'tier_range', 'is_pricelist'],
        loaded: function(self, load_tiers){
            var tier_by_id = {};
            var tiers = {};
            var tiers_list = [];
            $.each(load_tiers, function (i, tier) {
                tier_by_id[tier.id] = tier
                for(var i = tier.start_tier; i <= tier.end_tier; i++){
                    // list of priority 1 to 9
                    var priorities = [[],[],[],[],[],[],[],[],[]];
                    tiers[i] = priorities;
                    tiers_list.push(i);
                }
            });
            self.db.tier_by_id = tier_by_id;
            self.db.tiers = tiers;
        },
    },{
        model: 'pos.promotion',
        domain: function (self) {
            var now = new Date();
            var now_str = now.toISOString();
            return [
                ['id', 'in', self.branch.promotion_ids],
                ['date_end', '>=', now_str],
                ['active', '=', 'True'],
                ['is_channel_pos', '=', 'True'],
            ];
        },
        context: {active_test: false},
        order: ['tier', 'priority', 'sequence', 'id'],
        fields: ['sequence', 'branch_ids', 'promotion_code', 'promotion_name', 'promotion_segment', 'promotion_type', 'condition_type',
            'apply_with_coupon', 'condition_type_mapping', 'reward_type', 'date_start', 'date_end', 'is_best_deal',
            'promotion_condition_ids', 'active', 'is_custom_time', 'start_time', 'end_time', 'is_custom_day',
            'all_sunday', 'all_monday', 'all_tuesday', 'all_wednesday', 'all_thursday', 'all_friday', 'all_saturday',
            'first_sunday', 'first_monday', 'first_tuesday', 'first_wednesday', 'first_thursday', 'first_friday',
            'first_saturday', 'second_sunday', 'second_monday', 'second_tuesday', 'second_wednesday', 'second_thursday',
            'second_friday', 'second_saturday', 'third_sunday', 'third_monday', 'third_tuesday', 'third_wednesday',
            'third_thursday', 'third_friday', 'third_saturday', 'fourth_sunday', 'fourth_monday', 'fourth_tuesday',
            'fourth_wednesday', 'fourth_thursday', 'fourth_friday', 'fourth_saturday', 'last_sunday', 'last_monday',
            'last_tuesday', 'last_wednesday', 'last_thursday', 'last_friday', 'last_saturday', 'tier_id', 'tier_option_id',
            'tier', 'start_tier', 'priority', 'is_exclude_tier', 'exclude_tier_ids'
        ],
        loaded: function (self, promotions) {
            self.db.promotion_by_id = {};
            self.db.add_promotions(promotions);
        }
    }, {
        model: 'pos.promotion.condition',
        order: ['sequence', 'id'],
        fields: ['id', 'sequence', 'promotion_id', 'promotion_condition_name', 'condition_amount',
            'condition_bill_limit', 'condition_product', 'condition_brand_id', 'condition_categ_id',
            'condition_dept', 'condition_sub_dept',
            'reward_discount_percentage','reward_amount', 'reward_product', 'reward_categ_id', 'reward_brand_id',
            'reward_dept', 'reward_sub_dept', 'apply_to_reward',
            'reward_max_discount', 'is_exclude_product', 'exclude_condition_product', 'exclude_condition_brand_id',
            'exclude_condition_categ_id', 'exclude_condition_dept', 'exclude_condition_sub_dept',
            'exclude_condition_manual_product', 'promotion_condition_product_qty_ids', 'is_exclude_reward',
            'exclude_reward_product', 'exclude_reward_brand_id', 'exclude_reward_categ_id', 'exclude_reward_dept',
            'exclude_reward_sub_dept', 'exclude_reward_manual_product', 'is_select_product_discount',
            'condition_manual_product_ids', 'condition_mapping_product_qty_ids', 'reward_mapping_product_qty_ids',
            'is_condition_mapping_qty', 'is_reward_mapping_qty',
            'apply_with_coupon','is_free_as_same_pid' ,'condition_coupon_type', 'condition_coupon_product_id',
            'reward_coupon_type', 'reward_coupon_product_id',
        ],
        domain: function (self) {
            return [
                ['promotion_id', 'in', _.keys(self.db.promotion_by_id)]
            ];
        },
        loaded: function (self, promotion_condition_ids) {
            self.db.promotion_condition_ids = promotion_condition_ids;
            self.db.promotion_condition_by_id = {};
            self.db.add_promotion_conditions(promotion_condition_ids);

            //sort condition_ids
            for(var key in self.db.promotion_by_id){
                self.db.promotion_by_id[key].condition_ids.sort(function(a,b){
                    return b.condition_amount - a.condition_amount;
                });
            }
            self.db.promotions = _.values(self.db.promotion_by_id);
            // sorted by seq from smallest to largest
            self.db.promotions.sort(function(a,b){
                return a.sequence - b.sequence;
            });
            //var load_product_reward = []
            var load_promotion_condition_product_qty_list = [];
            //set condition by reward product on begin
            //var reward_product_ids = [];
            var product_coupon_ids = [];
            var coupon_multi_ids = [];
            var condition_by_rewrd_coupon_multi_id = {};
            self.db.promotions.sort(function(a, b){
                // sort by 'tier', 'priority', 'sequence', 'id'
                if(a.tier != b.tier)
                    return a.tier - b.tier;
                else if(a.priority != b.priority)
                    return a.priority != b.priority;
                else if(a.sequence != b.sequence)
                    return a.sequence != b.sequence;
                else
                    return a.id - b.id;
            }).forEach(function(promotion){
                promotion.condition_ids.forEach(function(condition){
                    var reward_products = condition.reward_manual_product;
                    if(promotion.apply_with_coupon && promotion.apply_with_coupon != 'no'){
                        var coupon_product_id = undefined;
                        if(condition[promotion.apply_with_coupon+'_coupon_product_id'] instanceof Array){
                            var product_id = condition[promotion.apply_with_coupon+'_coupon_product_id'][0];
                            if(product_id){
                                product_coupon_ids.push(product_id);
                                if(condition[promotion.apply_with_coupon+'_coupon_type'] == 'multi'){
                                    coupon_multi_ids.push(product_id)
                                    if(promotion.apply_with_coupon == 'reward'){
                                        if(!(product_id in condition_by_rewrd_coupon_multi_id))
                                            condition_by_rewrd_coupon_multi_id[product_id] =  [];
                                        condition_by_rewrd_coupon_multi_id[product_id].push(condition);
                                    }
                                }
                            }
                        }
                    }
                    if(condition.condition_manual_product_ids && condition.condition_manual_product_ids.length > 0){
                        load_promotion_condition_product_qty_list = load_promotion_condition_product_qty_list.concat(condition.condition_manual_product_ids);
                    }
                    if(condition.condition_mapping_product_qty_ids && condition.condition_mapping_product_qty_ids.length > 0){
                        load_promotion_condition_product_qty_list = load_promotion_condition_product_qty_list.concat(condition.condition_mapping_product_qty_ids);
                    }
                    if(condition.reward_mapping_product_qty_ids && condition.reward_mapping_product_qty_ids.length > 0){
                        load_promotion_condition_product_qty_list = load_promotion_condition_product_qty_list.concat(condition.reward_mapping_product_qty_ids);
                    }
                });
                self.db.tiers[promotion.tier][promotion.priority].push(promotion);
            });

            self.db.product_coupon_ids = product_coupon_ids;
            self.db.coupon_multi_ids = coupon_multi_ids;
            self.db.condition_by_rewrd_coupon_multi_id = condition_by_rewrd_coupon_multi_id;
            self.db.load_promotion_condition_product_qty_list = load_promotion_condition_product_qty_list;

            //self.db.load_product_reward = load_product_reward;
            if(self.db.template_product_ids instanceof Array){
                self.db.template_product_ids = _.union(self.db.template_product_ids, product_coupon_ids);
            }
            else{
                self.db.template_product_ids = product_coupon_ids;
            }
        },
    }, {
        model: 'promotion.mapping.product.qty',
        fields: ['id', 'model_type', 'promotion_condition_id', 'product_id_int', 'qty', 'is_mapping_qty'],
//        domain: (self) => [['id', 'in', self.db.load_promotion_condition_product_qty_list]],
        domain: (self) => [['promotion_condition_id', 'in', _.keys(self.db.promotion_condition_by_id)]],
        loaded: function (self, product_qty_ids) {
            self.db.promotion_condition_product_qty_by_id = {};
            self.db.add_promotion_condition_product_qty(product_qty_ids);
        },
    },{
        model: 'multi.coupon',
        fields: ['id','product_id_int', 'barcode'],
        domain: function(self){
            return [['product_id', 'in', self.db.coupon_multi_ids]];
        },
        loaded: function (self, coupons) {
            var multi_coupon_by_id = {};
            var multi_coupon_by_barcode = {};
            coupons.forEach(function(coupon){
                coupon.barcode_image_base64 = self.db.get_barcode_image(coupon.barcode);
                multi_coupon_by_id[coupon.id] = coupon;
                multi_coupon_by_barcode[coupon.barcode] = coupon;
            });
            self.db.multi_coupon_by_id = multi_coupon_by_id;
            self.db.multi_coupon_by_barcode = multi_coupon_by_barcode;
        },
    }], {'before': 'product.product'});


    var ConfirmPromotionPopupWidget = popups.extend({
        template: 'ConfirmPromotionPopupWidget',
    });
    gui.define_popup({name: 'confirm_promotion', widget: ConfirmPromotionPopupWidget});

    var ConfirmPromotionOrderlinePopupWidget = popups.extend({
        template: 'ConfirmPromotionOrderlinePopupWidget',
    });
    gui.define_popup({name: 'confirm_promotion_orderline', widget: ConfirmPromotionOrderlinePopupWidget});

    var ZeroTotalWithTaxPopupWidget = popups.extend({
        template: 'ZeroTotalWithTaxPopupWidget',
    });
    gui.define_popup({name: 'zero_with_tax_popup', widget: ZeroTotalWithTaxPopupWidget});

    var timeout = null;
    screens.OrderWidget.include({
        set_value: function (val) {
            var order = this.pos.get_order();
            this._super(val);
            order.reverse_promotions();
        },
        /*update_summary: function () {
            this._super();
            var order = this.pos.get_order();
            var self = this;
            if (timeout) {
                clearTimeout(timeout);
            }
            timeout = setTimeout(function () {

                if (self.getParent().action_buttons
                    && self.getParent().action_buttons.promotion ) {
                    self.getParent().action_buttons.promotion.highlight(order.has_promotion());
                }
            }, 0);
        },*/
    });

    var PromotionScreenWidget = screens.ScreenWidget.extend({
        template: 'PromotionScreenWidget',
        previous_screen: 'products',
        init: function (parent) {
            this._super(parent);

            this.result_promotions = [];
            this.pass_threshold = [];
            this.require_free_product = [];
        },
        bind_events: function(){

        },
        kill_promotion: function(promotion, killed_index = -1){
            var self = this;
            var order = self.pos.get_order();
            if(order){
                if(killed_index == -1)
                    order.killed_promotions.push(promotion);
                else
                    order.killed_promotions.splice(killed_index, 1);

                self.render_suggest_promotion_detail();
            }
        },
        render_promotion_lines: function(promotion_order){
            var promotions_lines = $(QWeb.render('SuggestPromotionList', {
                widget: this,
                promotions: promotion_order || []
            }));
            return promotions_lines;
        },
        render_promotions_container: function(){
            var self = this;
            var promotion_container = this.$('div.promotions-container');
            promotion_container.empty();
            this.result_promotions.forEach(function(tier){
                tier.promotions && tier.promotions.forEach(function(promotion){
                    promotion.promotion_onclick = true;
                });
            });
            var promotion_lines = this.render_promotion_lines(this.result_promotions);
            promotion_lines.appendTo(promotion_container);

            promotion_container.off('click');
            promotion_container.on('click', '.line', function(event){
                var $this = $(this);
                var idx = $this.attr('idx');
                var jdx = $this.attr('jdx');

                var order = self.pos.get_order();
                if(order){
                    if(self.result_promotions.length > 0 && self.result_promotions[idx]
                    && self.result_promotions[idx].promotions.length > 0 && self.result_promotions[idx].promotions[jdx]
                    && self.result_promotions[idx].promotions[jdx].promotion_id
                    && self.result_promotions[idx].promotions[jdx].promotion_condition_id){
                        var promotion = {
                            promotion_id: self.result_promotions[idx].promotions[jdx].promotion_id,
                            condition_id: self.result_promotions[idx].promotions[jdx].promotion_condition_id,
                        };
                        var killed_index = order.killed_promotions.findIndex(function(item){
                            return item.promotion_id == promotion.promotion_id
                                && item.condition_id == promotion.condition_id;
                        });

                        var call_kill_function = function(){
                            self.ask_manager_ask_pin().then(function(approver){
                                self.kill_promotion(promotion, killed_index);
                            });
                        };

                        if(killed_index == -1)
                            self.gui.show_popup('confirm', {
                                'title': 'Kill Promotion',
                                'body': 'คุณต้องการยกเลิกโปรโมชั่นนี้ใช่หรือไม่',
                                confirm: call_kill_function,
                            });
                        else
                            call_kill_function();
                    }
                }
                return true;
            });
        },
        render_return_coupons_container: function(){
            var removed_coupons = _.values(this.pos.get_order().removed_coupons).reduce((arr, item)=>arr.concat(item), []);

            var return_coupons = [];
            var product_by_id = this.pos.db.product_by_id;
            removed_coupons.forEach(function(removed_coupon){
                var coupon = product_by_id[removed_coupon.product_id]
                var name = '[' + (removed_coupon.coupon_barcode || coupon.barcode) + '] ' + coupon.name;
                return_coupons.push({
                    name: name,
                    amount: removed_coupon.quantity,
                    selected: true,
                })
            });
            if(return_coupons.length > 0)
                return_coupons = [{promotions: return_coupons}];

            this.$('div.return-coupons-container').empty();
            var promotion_lines = this.render_promotion_lines(return_coupons);
            promotion_lines.appendTo(this.$('div.return-coupons-container'));
        },
        render_suggest_container: function(){
            var pass_threshold = (this.pass_threshold.length > 0)?[{promotions:this.pass_threshold}]:[];
            this.$('div.suggest-container').empty();
            var promotion_lines = this.render_promotion_lines(pass_threshold);
            promotion_lines.appendTo(this.$('div.suggest-container'));
        },
        render_free_product_container: function(){
            var require_free_product = (this.require_free_product.length > 0)?[{promotions:this.require_free_product}]:[];
            this.$('div.free-product-container').empty();
            var promotion_lines = this.render_promotion_lines(require_free_product);
            promotion_lines.appendTo(this.$('div.free-product-container'));
        },
        render_orderlines: function(self, orderlines){
            var html = '<div class="order"><div class="orderlines">';
            orderlines.forEach(function(orderline){
                html += QWeb.render('Orderline',{widget:self, line:orderline});
            });
            html += '</div></div>';
            return html;
        },
        render_total_to_paid: function(){
            return QWeb.render('TotalToPaid',{
                amount_total: this.format_currency(this.pos.get_order().get_total_with_tax()),
            });
        },
        compute_promotion: function(){
            var result = this.pos.get_order().apply_promotions();
            this.result_promotions = result.result_promotions;
            this.pass_threshold = result.pass_threshold;
            this.require_free_product = result.require_free_product;
        },
        render_suggest_promotion_detail: function(){
            var self = this;
            this.compute_promotion();

            this.render_promotions_container();
            this.render_return_coupons_container();
            this.render_suggest_container();
            this.render_free_product_container();
            var total_to_paid = this.render_total_to_paid()
            this.$el.find('.title-before-next').html(total_to_paid);
        },
        click_next: function(self){
            var total_to_paid = self.render_total_to_paid()
            if(self.result_promotions.length > 0){
                self.pos.gui.show_popup('confirm_promotion_orderline', {
                    'title': 'สรุปโปรโมชั่นที่ได้รับ',
                    'body': self.render_orderlines(self, self.pos.get_order().get_orderlines().filter((line)=>line.promotion)),
                    'bottom_tittle': '<div style="margin-top: 10px; margin-left: 10px; line-height: 36px;">'
                                    + total_to_paid + '</div>',
                    'confirm': function (){
                        self.pos.gui.show_screen('payment');
                    },
                    'cancel': function () {
                    },
                });
            }
            else{
                self.pos.gui.show_screen('payment');
            }
            return;
        },
        click_back: function(self){
            self.pos.get_order().reverse_promotions();
            self.gui.show_screen(self.previous_screen);
        },
        show: function() {
            var self = this;
            this._super();

            var order = this.pos.get_order();

            if(order.is_calculated_promotion){
                order.reverse_promotions();
            }

            this.render_suggest_promotion_detail();

            this.pos.db.multi_coupon_validation().then(function(result){
                if(result && result.length){
                    self.render_suggest_promotion_detail();
                }
            });

            this.$('.screen-content').off('click', '.button.next');
            this.$('.screen-content').off('click', '.button.back');

            this.$('.screen-content').on('click', '.button.next', function (e) {
                self.click_next(self)
            });
            this.$('.screen-content').on('click', '.button.back', function (e) {
                self.click_back(self);
            });

        },
    });

    gui.define_screen({
        'name': 'promotion',
        'widget': PromotionScreenWidget,
        'condition': function () {
            return true;
        },
    });

    screens.NumpadWidget.include({
        clickDeleteLastChar: function() {
            var order = this.pos.get_order();
            if(order.is_calculated_promotion){
                order.reverse_promotions();
            }

            var selected_orderline = order.get_selected_orderline();
            if (selected_orderline && selected_orderline.product.is_coupon
            && selected_orderline.product.coupon_type == 'multi'&& selected_orderline.coupon_barcode) {
                this.pos.db.unreserved_reserve_coupon(selected_orderline.product.id, selected_orderline.coupon_barcode);
                if(selected_orderline.remove_timeout)
                    clearTimeout(selected_orderline.remove_timeout);
                order.remove_orderline(selected_orderline);

                if(!order.has_multi_coupon_with_barcode()){
                    //cannot find, then unset order to temporary
                    order.temporary = false;
                }
                return;
            }
            return this._super();
        },
        clickAppendNewChar: function(event) {
            var order = this.pos.get_order();
            if(order.is_calculated_promotion){
                order.reverse_promotions();
            }

            var selected_orderline = order.get_selected_orderline();
            if (selected_orderline && selected_orderline.product.is_coupon && selected_orderline.coupon_barcode) {
                return;
            }
            return this._super(event);
        },
        clickDecrease: function (event) {
            var order = this.pos.get_order();
            if(order.is_calculated_promotion){
                order.reverse_promotions();
            }

            var selected_orderline = order.get_selected_orderline();
            if (selected_orderline && selected_orderline.product.is_coupon
            && selected_orderline.product.coupon_type == 'multi' && selected_orderline.coupon_barcode) {
                this.pos.db.unreserved_reserve_coupon(selected_orderline.product.id, selected_orderline.coupon_barcode);
                if(selected_orderline.remove_timeout)
                    clearTimeout(selected_orderline.remove_timeout);
                order.remove_orderline(selected_orderline);

                if(!order.has_multi_coupon_with_barcode()){
                    //cannot find, then unset order to temporary
                    order.temporary = false;
                }
                return;
            }
            return this._super(event);
        },
        clickIncrease: function (event) {
            var order = this.pos.get_order();
            if(order.is_calculated_promotion){
                order.reverse_promotions();
            }

            var selected_orderline = order.get_selected_orderline();
            if (selected_orderline && selected_orderline.product.is_coupon && selected_orderline.coupon_barcode) {
                return;
            }
            return this._super(event);
        },
    });

    screens.ActionpadWidget.include({
        click_pay: function(self){
            var orderlines = self.pos.get_order().get_orderlines();
            var filtered_lines = orderlines.filter((line) => line.quantity > 0  && !line.product.is_coupon);
            if(filtered_lines.length == 0){
                return;
            }
            this._super(self);
        },
        change_page: function(self){
            if(self.pos.system_parameter_pos_promotion){
                self.gui.show_screen('promotion');
            }
            else{
                self.gui.show_screen('payment');
            }
        },
    });

    screens.PaymentScreenWidget.include({
        request_barcode_reward_coupon: function(){
            var self = this;
            var deferred = $.Deferred();
            var no_barcode_coupon = this.pos.get_order().find_reward_coupons_wo_barcode();

            this.pos.chrome.loading_show();
            this.pos.chrome.loading_message('กรุณารอสักครู่ ระบบตรวจสอบคูปอง', 0.4);

            var request_list = [];
            var result_list = false;

            var product_ids = [];
            var line_by_product = {};
            no_barcode_coupon.forEach(function(line){
                product_ids.push(line.product.id);
                line_by_product[line.product.id] = line;
            });

            request_list.push(self.pos.db.get_barcode_coupon(product_ids).then(function(result){
                result_list = result;
            }));

            this.pos.chrome.loading_message('กรุณารอสักครู่ ระบบตรวจสอบคูปอง', 0.7);

            $.when.apply($, request_list).then(function(){
                var no_barcode = [];
                if(result_list && 'status' in result_list && result_list.status == 'success'){
                    var multi_coupon_by_id = self.pos.db.multi_coupon_by_id;
                    product_ids.forEach(function(product_id){
                        var line = line_by_product[product_id];
                        if(product_id in result_list && result_list[product_id] in multi_coupon_by_id){
                            var multi_coupon = multi_coupon_by_id[result_list[product_id]];
                            line.coupon_barcode = multi_coupon.barcode;
                            line.coupon_barcode_image_base64 = multi_coupon.barcode_image_base64;
                            line.multi_coupon_id = multi_coupon.id;
                        }
                        else
                            no_barcode.push(line);
                    });
                }
                else no_barcode = _.values(line_by_product);
                deferred.resolve(no_barcode);
            }, function(err){
                deferred.reject(err);
            }).always(function(){
                self.pos.chrome.loading_hide();
            });

            return deferred;
        },
        remove_orderlines_by_lines: function(order, lines){
            lines.forEach(function(line){
                order.remove_orderline(line);
            });
        },
        finalize_validation: function(){
            var self = this;
            var order = self.pos.get_order();
            // if (order.is_return_order || order.is_void_order){
            //     console.log('must cancel T1CP');
            //     self.chrome.loading_show();
            //     self.batch_cancel_redeem_tender().then(function(result){
            //         self.chrome.loading_hide();
            //     });
            // }
            var reward_coupons_wo_barcode = order.find_reward_coupons_wo_barcode();
            if(reward_coupons_wo_barcode.length > 0){
                this.request_barcode_reward_coupon(reward_coupons_wo_barcode).then(function(no_barcode_coupon){
                    if(no_barcode_coupon.length)
                        self.remove_orderlines_by_lines(order, no_barcode_coupon);
                    self.finalize_validation();
                }, function(err){
                    self.pos.gui.show_popup('confirm_promotion', {
                        'title': 'ไม่สามารถเชื่อมต่อกับส่วนออกคูปองได้',
                        'body': 'อาจส่งผลให้ลูกค้าไม่ได้รับคูปอง<br/>จะดำเนินการ กด "เชื่อมต่ออีกครั้ง" หรือ<br/>กด "ข้าม" เพื่อข้ามขั้นตอนการออกคูปอง',
                        'confirm_title': 'เชื่อมต่ออีกครั้ง',
                        'cancel_title': 'ข้าม',
                        confirm: function(){
                            self.finalize_validation();
                        },
                        cancel:  function(){
                            var reward_coupons_wo_barcode = order.find_reward_coupons_wo_barcode();
                            self.remove_orderlines_by_lines(order, reward_coupons_wo_barcode);
                            self.finalize_validation();
                        },
                    });
                    return false;
                });
            }
            else{
                // remove timeout of multi coupon clean
                order.get_orderlines().forEach(function(line){
                    if(line.remove_timeout)
                        clearTimeout(line.remove_timeout);
                });
                this._super();
            }
        },
        click_back: function(){
            if(this.pos.system_parameter_pos_promotion){
                this.gui.show_screen('promotion');
            }
            else{
                this.gui.show_screen('products');
            }
        },
    });

    screens.ProductScreenWidget.include({
        show: function () {
            this._super();
            this.pos.db.multi_coupon_validation(true);
        },
    });

    return PromotionScreenWidget;
});