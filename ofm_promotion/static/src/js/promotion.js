odoo.define('ofm_promotion.promotion', function (require) {
    "use strict";

    var gui = require('point_of_sale.gui');
    var models = require('point_of_sale.models');
    var PosDB = require('point_of_sale.DB');
    var screens = require('point_of_sale.screens');
    var popups = require('point_of_sale.popups');
    var core = require('web.core');
    var session = require('web.session');
    var utils = require('web.utils');
    var round_pr = utils.round_precision;

    var _t = core._t;
    var QWeb = core.qweb;

    var lastOfMonth = function(date = undefined){
        date = date || new Date();
        return (new Date(date.getFullYear(), date.getMonth() +1, 0));
    };

    var firstOfMonth = function(date = undefined){
        date = date || new Date();
        return new Date(date.getFullYear(), date.getMonth(), 1);
    };

    var nthWeekOfMonth = function(input = undefined){
        input = input || new Date();
        var date = input.getDate()
        return {
            date: date,
            day: input.getDay(),
            week: Math.ceil(date/7),
            islast: (date + 7 > lastOfMonth(input).getDate())?true:false,
        }
    };

    var numToText = {1: 'first', 2: 'second', 3: 'third', 4: 'fourth', 5: 'fifth'};

    var numToDay ={
        0: 'sunday', 1: 'monday', 2: 'tuesday', 3: 'wednesday',
        4: 'thursday', 5: 'friday', 6: 'saturday',
    }

    var _super_order = models.Order;
    models.Order = models.Order.extend({
        initialize: function (attributes, options) {
            //_super_order
            this.removed_coupons = {};
            _super_order.prototype.initialize.call(this, attributes, options);
            //this.promotion_order = [];
            this.killed_promotions = [];

            this.on_reverse_promotion_process = false;
        },
        init_from_JSON: function (json) {
            //this.promotion_order = json.promotion_order;
            this.killed_promotions = json.killed_promotions;
            this.removed_coupons = json.removed_coupons;
            _super_order.prototype.init_from_JSON.call(this, json);
            this.is_calculated_promotion = this.is_applied_promotion();
        },
        export_as_JSON: function () {
            var data = _super_order.prototype.export_as_JSON.call(this);
            //data.promotion_order = this.promotion_order;
            data.killed_promotions = this.killed_promotions;
            data.before_discount = this.get_subtotal_without_discount();
            data.removed_coupons = this.removed_coupons;
            return data;
        },
        has_promotion: function () {
            var has_promotion = this.promotion_order.length;
            return !!has_promotion;
        },
        has_reward_coupon: function(){
            var lines = this.get_orderlines();
            for(var i = 0; i < lines.length ; i++){
                if(lines[i].line_coupon == 'reward_coupon'){
                    return true;
                }
            }
            return false;
        },
        has_multi_coupon_with_barcode: function(){
            var lines = this.get_orderlines();
            for(var i = 0; i < lines.length ; i++){
                var line = lines[i];
                if(line.product.is_coupon && line.product.coupon_type == 'multi'
                && line.multi_coupon_id && line.coupon_barcode){
                    return true;
                }
            }
            return false;
        },
        find_reward_coupons_wo_barcode: function(){
            var no_barcode_coupon = [];
            var lines = this.get_orderlines();
            for(var i = 0; i < lines.length ; i++){
                if(lines[i].line_coupon == 'reward_coupon' && lines[i].product.coupon_type == 'multi' && !lines[i].coupon_barcode){
                    no_barcode_coupon.push(lines[i]);
                }
            }
            return no_barcode_coupon;
        },
        is_applied_promotion: function(){
            var order = this;
            var lines = this.get_orderlines();
            for(var idx = 0; idx < lines.length ; idx ++){
                if(lines[idx].promotion)
                    return true;
            }
            return false;
        },
        reverse_promotions: function(){
            var self = this;
            var order = this;
            if(order.is_applied_promotion() || order.is_calculated_promotion){
                this.on_reverse_promotion_process = true;
                var promotion_product_id = this.pos.config.promotion_discount_product_id[0];
                var lines = order.get_orderlines();
                var dict_product = {};
                var remove_lines = [];
                lines.forEach(function(line){
                    var product_id = line.product.id;
                    if(!line.force_add && !line.line_coupon && product_id != promotion_product_id){
                        if(product_id in dict_product){
                            var selected_line = dict_product[product_id];
                            selected_line.set_quantity(selected_line.quantity + line.quantity);
                            remove_lines.push(line);
                        }
                        else{
                            line.promotion = false;
                            line.promotion_id = false;
                            line.promotion_type = false;
                            line.reward_type = false;
                            line.promotion_condition_id = false;
                            dict_product[product_id] = line;
                            line.prorate_amount = 0.0;
                            line.prorate_amount_exclude = 0.0;
                            line.prorate_vat = 0.0;
                            line.prorate_amount_2 = 0.0;
                            line.prorate_amount_exclude_2 = 0.0;
                            line.prorate_vat_2 = 0.0;
                            line.tiers = [];
                            line.prorate_ids = [];
                        }
                    }
                    else{
                        remove_lines.push(line);
                    }
                });
                remove_lines.forEach(function(line){
                    order.remove_orderline(line);
                });
                if(order.removed_coupons){
                    _.values(order.removed_coupons).forEach(function(removed_coupons){
                        removed_coupons.forEach(function(removed_coupon){
                            if(removed_coupon.coupon_barcode){
                                var product = self.pos.db.product_by_id[removed_coupon.product_id];
                                _super_order.prototype.add_product.call(order, product, {
                                    price: 0,
                                    quantity: removed_coupon.quantity,
                                    multi_line: true,
                                    extras: {
                                        coupon_barcode: removed_coupon.coupon_barcode,
                                        multi_coupon_id: removed_coupon.multi_coupon_id,
                                    },
                                });
                            }
                            else{
                                var orderline = order.get_orderline_by_product_id(removed_coupon.product_id);
                                if(orderline){
                                    orderline.quantity = parseInt(orderline.quantity + removed_coupon.quantity);
                                    orderline.quantityStr = '' + orderline.quantity;
                                }
                                else{
                                    var product = self.pos.db.product_by_id[removed_coupon.product_id];
                                    _super_order.prototype.add_product.call(order, product, {quantity: removed_coupon.quantity});
                                }
                            }
                        });
                    });
                    order.removed_coupons = {};
                }
                this.trigger('change',this);
                this.pos.chrome.screens.products.order_widget.renderElement();
                this.on_reverse_promotion_process = false;
            }
            this.is_calculated_promotion = false;
        },
        add_product: function (product, options) {
            var screen_name = this.pos.gui.get_current_screen();
            if (screen_name == 'products' && this.is_calculated_promotion) {
                this.reverse_promotions();
            }
            _super_order.prototype.add_product.call(this, product, options);
        },
        get_promotion_line_name: function(promotion_id, condition_id, product_id = undefined){
            var self = this;
            var promotion = self.pos.db.promotion_by_id[promotion_id];
            var condition = self.pos.db.promotion_condition_by_id[condition_id];

            var name = promotion.promotion_code + ' ';
            if(promotion.reward_type == 'product'){
                if(product_id){
                    name += 'แถม ' + self.pos.db.product_by_id[product_id].display_name;
                }
                else{
                    name += 'ของแถมจาก' + promotion.promotion_name;
                }
            }
            else if(promotion.reward_type == 'discount'){
                name += promotion.promotion_name;
            }
            return name;
        },
        promotions_validation: function(){
            var self = this;
            var branch_id = self.pos.branch.id;
            var now = new Date();
            var now_float_time = now.getHours() + now.getMinutes()*100/6000;
            var nthWeek = nthWeekOfMonth(now);

            var promotion_list = {};

            _.keys(self.pos.db.tiers).forEach(function(tier){
                self.pos.db.tiers[tier].forEach(function(priority, idx){
                    priority.forEach(function(promotion){
                        if( promotion.active && (promotion.branch_ids.includes(branch_id))
                        && ( (new Date(promotion.date_start+'Z')) <= now)
                        && ( (new Date(promotion.date_end+'Z')) >= now) ){
                            var add = true;
                            if(promotion.is_custom_time || promotion.is_custom_day){
                                if(promotion.is_custom_day)
                                    if(promotion['all_'+numToDay[nthWeek.day]]
                                    || (nthWeek.islast && promotion['last_'+numToDay[nthWeek.day]])
                                    || promotion[numToText[nthWeek.week]+'_'+numToDay[nthWeek.day]])
                                        add = true;
                                    else
                                        add = false;
                                else
                                    add = true;
                                if(promotion.is_custom_time)
                                    if(add && promotion.is_custom_time && promotion.start_time <= now_float_time
                                    && now_float_time < promotion.end_time)
                                        add = true;
                                    else
                                        add = false;
                                else
                                    add = true;
                            }
                            if(add){
                                if(!(tier in promotion_list)){
                                    promotion_list[tier] = [[],[],[],[],[],[],[],[],[]];
                                }
                                promotion_list[tier][idx].push(promotion);
                            }
                        }
                    });
                });
            });
            return promotion_list;
        },
        calculate_sub: function(condition_type, reward_type, is_best_deal ,origin_lines, domain,
                                exclude_domain = false, exclude_tiers = false, included_promotion = false){
            var self = this;
            var lines = self.check_and_clone_orderlines(origin_lines);

            if(!is_best_deal){
                lines = lines.filter(line => !line.product.is_best_deal_promotion);
            }

            if(!included_promotion){
                lines = lines.filter((line)=> !line.promotion);
            }
            if(domain.condition_product == 'brand'){
                if(domain.condition_apply_id in self.pos.db.product_by_brand_id)
                    lines = lines.filter((line) => self.pos.db.product_by_brand_id[domain.condition_apply_id].product_ids.includes(line.product.id));
                else
                    lines = [];
            }
            else if(domain.condition_product == 'category'){
                if(domain.condition_apply_id in self.pos.db.product_by_categ_id)
                    lines = lines.filter((line) => self.pos.db.product_by_categ_id[domain.condition_apply_id].product_ids.includes(line.product.id));
                else
                    lines = [];
            }
            else if(domain.condition_product == 'dept' || domain.condition_product == 'sub_dept'){
                if(domain.condition_apply_id in self.pos.db.product_by_dept_id)
                    lines = lines.filter((line) => self.pos.db.product_by_dept_id[domain.condition_apply_id].product_ids.includes(line.product.id));
                else
                    lines = [];
            }
            else if(domain.condition_product == 'manual'){
                lines = lines.filter((line) => domain.condition_manual_product.includes(line.product.id));
            }

            if(exclude_domain){
                if(exclude_domain.exclude_condition_product == 'brand'){
                    if(exclude_domain.exclude_condition_apply_id in self.pos.db.product_by_brand_id)
                        lines = lines.filter((line) => !self.pos.db.product_by_brand_id[exclude_domain.exclude_condition_apply_id].product_ids.includes(line.product.id));
                }
                else if(exclude_domain.exclude_condition_product == 'category'){
                    if(exclude_domain.exclude_condition_apply_id in self.pos.db.product_by_categ_id)
                        lines = lines.filter((line) => !self.pos.db.product_by_categ_id[exclude_domain.exclude_condition_apply_id].product_ids.includes(line.product.id));
                }
                else if(exclude_domain.exclude_condition_product == 'dept' || exclude_domain.exclude_condition_product == 'sub_dept'){
                    if(exclude_domain.exclude_condition_apply_id in self.pos.db.product_by_dept_id)
                        lines = lines.filter((line) => !self.pos.db.product_by_dept_id[exclude_domain.exclude_condition_apply_id].product_ids.includes(line.product.id));
                }
                else if(exclude_domain.exclude_condition_product == 'manual'){
                    lines = lines.filter((line) => !exclude_domain.exclude_condition_manual_product.includes(line.product.id));
                }
            }

            if(exclude_tiers && _.isArray(exclude_tiers)){
                lines = lines.filter(function(line){
                    for(var i = 0; i < line.tiers.length; i++){
                        for(var j = 0; j < exclude_tiers.length; j++){
                            var ex_tier = exclude_tiers[j];
                            if(ex_tier.start_tier <= line.tiers[i] && line.tiers[i] <= ex_tier.end_tier){
                                return false;
                            }
                        }
                    }
                    return true;
                });
            }

            var sub = 0;
            var sub_exclude = 0.0;
            var tax = 0.0
            var orderline_model = self.orderlines.models[0];
            var line_ids = [];
            if(condition_type == 'price'){
                var subtotal = 0.0;
                var subtotal_exclude = 0.0;
                var temp_tax = 0.0
                lines.forEach(function(line){
                    var total = (line.price * line.quantity) - line.prorate_amount;
                    var all_price = orderline_model.get_all_prices_by_subtotal(total, line.product)
                    subtotal += all_price.priceWithTax;
                    subtotal_exclude  += all_price.priceWithoutTax;
                    temp_tax += all_price.tax;
                    line_ids.push(line.id);
                });
                sub = subtotal;
                sub_exclude = subtotal_exclude;
                tax = temp_tax;
            }
            else if(condition_type == 'qty'){
                var  subqty = 0;
                lines.forEach(function(line){
                    subqty += line.quantity;
                    line_ids.push(line.id);
                });
                sub = subqty;
            }
            return {
                sub: sub,
                sub_exclude: sub_exclude,
                tax: tax,
                condition_type: condition_type,
                lines: lines,
                line_ids: line_ids,
            };
        },
        calculate_step_promotion: function(lines, promotion, coupon){
            var self = this;
            var conditions = promotion.condition_ids;
            var steps = [];
            //condition list is sorted
            var condition_type = promotion.condition_type;
            var reward_type = promotion.reward_type;
            var is_best_deal = promotion.is_best_deal;

            for(var idx = 0 ; idx < conditions.length ; idx++){
                if(promotion.apply_with_coupon != 'condition' || (promotion.apply_with_coupon == 'condition'
                && conditions[idx].condition_coupon_product_id
                && conditions[idx].condition_coupon_product_id[0] in coupon.ids)){
                    var success = false;
                    if(conditions[idx].is_condition_mapping_qty){
                        var found_all = true;
                        conditions[idx].condition_mapping_product_qty_ids.forEach(function(product_qty){
                            if(found_all){
                                var amount = lines.filter((line) => line.product.id == product_qty.product_id_int).reduce(function(sum, line){
                                    return sum + line.quantity;
                                }, 0);
                                if(amount <= 0){
                                    found_all = false;
                                }
                            }
                        });
                        if(found_all)
                            success = true;
                    }
                    else{
                        var condition_product = conditions[idx].condition_product;
                        var condition_apply_id = conditions[idx].condition_apply_id;
                        var condition_manual_product = conditions[idx].condition_manual_product;
                        var condition_amount = conditions[idx].condition_amount;

                        var parameters = [
                            condition_type, reward_type, is_best_deal,
                            lines, {
                                condition_product: condition_product,
                                condition_apply_id: condition_apply_id,
                                condition_manual_product: condition_manual_product
                            }
                        ];

                        if(conditions[idx].is_exclude_product)
                            parameters.push({
                                exclude_condition_product: conditions[idx].exclude_condition_product,
                                exclude_condition_apply_id: conditions[idx].exclude_condition_apply_id,
                                exclude_condition_manual_product: conditions[idx].exclude_condition_manual_product
                            });
                        else
                            parameters.push(false);

                        var calulated = self.calculate_sub.apply(self, parameters);
                        if(calulated.sub > 0 && calulated.sub >= condition_amount)
                            success = true;
                    }
                    if(success){
                        steps.push({
                            condition_id: conditions[idx].id,
                            qty: 1,
                        });
                        break;
                    }
                }
            }
            if(steps.length == 0){
                steps.push({
                    condition_id: conditions[conditions.length-1].id,
                    qty: 0
                });
            }
            return steps;
        },
        calculate_loop_promotion: function(lines, promotion, coupon){
            var self = this;
            var conditions = promotion.condition_ids;
            var loops = [];
            //condition list is sorted
            var condition_type = promotion.condition_type;
            var reward_type = promotion.reward_type;
            var is_best_deal = promotion.is_best_deal;

            for(var idx = 0 ; idx < conditions.length ; idx++){
                var time = 0;
                //only case for condition by product
                if(promotion.apply_with_coupon != 'condition' || (promotion.apply_with_coupon == 'condition'
                && conditions[idx].condition_coupon_product_id
                && conditions[idx].condition_coupon_product_id[0] in coupon.ids)){
                    if(conditions[idx].is_condition_mapping_qty){
                        var not_found = true;
                        conditions[idx].condition_mapping_product_qty_ids.forEach(function(product_qty){
                            var amount = lines.filter((line) => line.product.id == product_qty.product_id_int).reduce(function(sum, line){
                                return sum + line.quantity;
                            }, 0);

                            if(not_found && amount > 0){
                                var new_time = parseInt( amount/product_qty.qty );
                                if(time == 0 || new_time < time)
                                    time = new_time
                            }
                            else{
                                not_found = false;
                            }
                        });
                    }
                    else{
                        var condition_bill_limit = conditions[idx].condition_bill_limit;
                        var condition_product = conditions[idx].condition_product;
                        var condition_apply_id = conditions[idx].condition_apply_id;
                        var condition_manual_product = conditions[idx].condition_manual_product;
                        var condition_amount = conditions[idx].condition_amount;

                        var parameters = [
                            condition_type, reward_type, is_best_deal,
                            lines, {
                                condition_product: condition_product,
                                condition_apply_id: condition_apply_id,
                                condition_manual_product: condition_manual_product
                            }
                        ];

                        if(conditions[idx].is_exclude_product)
                            parameters.push({
                                exclude_condition_product: conditions[idx].exclude_condition_product,
                                exclude_condition_apply_id: conditions[idx].exclude_condition_apply_id,
                                exclude_condition_manual_product: conditions[idx].exclude_condition_manual_product
                            });
                        else
                            parameters.push(false);

                        var calulated = self.calculate_sub.apply(self, parameters);
                        if(calulated.sub > 0 && condition_amount > 0 && calulated.sub >= condition_amount){
                            var amount = 1;
                            time = parseInt( calulated.sub/condition_amount );

                        }
                    }
                    if(time > 0){
                        if(promotion.apply_with_coupon == 'condition'
                        && conditions[idx].condition_coupon_product_id
                        && conditions[idx].condition_coupon_product_id[0] in coupon.ids){
                            var coupon_no = coupon.ids[conditions[idx].condition_coupon_product_id[0]].reduce(function(sum, line){
                                return sum  + line.quantity;
                            }, 0);
                            if(coupon_no < time){
                                time = coupon_no;
                            };
                        }

                        if(condition_bill_limit == 0)
                            amount = time;
                        else if(condition_bill_limit < time)
                            amount = condition_bill_limit;
                        else
                            amount = time;

                        loops.push({
                            condition_id: conditions[idx].id,
                            qty: amount
                        });
                    }
                    else{
                        //all to go
                        loops.push({
                            condition_id: conditions[idx].id,
                            qty: 0
                        });
                    }
                }
            }
            return loops;
        },
        calculate_promotion: function(coupon){
            var self = this;
            self.promotion_order = {};

            //pre check promotion is valid
            var order = self.pos.get_order();
            var tiers = self.promotions_validation();

            var lines = order.orderlines.models;

            var lines_wo_coupon = lines.filter(line => !line.product.is_coupon);

            _.keys(tiers).forEach(function(tier){
                self.promotion_order[tier] = [[],[],[],[],[],[],[],[],[]];
                tiers[tier].forEach(function(priority, idx){
                    priority.forEach(function(promotion){
                        var suggest_conditions_ids = undefined;
                        if(promotion.promotion_type === 'step'){
                            //given one number if success
                            suggest_conditions_ids = self.calculate_step_promotion(lines_wo_coupon, promotion, coupon);
                        }
                        else if(promotion.promotion_type === 'loop'){
                            suggest_conditions_ids = self.calculate_loop_promotion(lines_wo_coupon, promotion, coupon);
                        }
                        //prepare data
                        if(suggest_conditions_ids && suggest_conditions_ids.length > 0){
                            suggest_conditions_ids.forEach(function(condition){
                                self.promotion_order[tier][idx].push({
                                    //data for adding into orderline
                                    promotion_id: promotion.id,
                                    promotion_condition_id: condition.condition_id,
                                    //product_id: self.pos.db.promotion_condition_by_id[condition.condition_id].reward_manual_product[0],
                                    //data for real promotion and apply promotion, print
                                    target: condition.qty,
                                    qty: condition.qty,
                                    name: self.pos.db.promotion_by_id[promotion.id].promotion_name,
                                });
                            });
                        }
                    });
                })
            });
            return self.promotion_order;
        },
        clone_orderlines: function(orderlines){
            var new_orderlines = [];
            orderlines.forEach(function(line){
                var new_line = line.export_as_JSON();
                new_line.product = line.product;
                new_orderlines.push(new_line);
            });
            return new_orderlines;
        },
        check_and_clone_orderlines: function(origin_lines){
            if(origin_lines[0].pos || origin_lines[0].order)
                return this.clone_orderlines(origin_lines);
            else
                return _.recursiveDeepCopy(origin_lines);
        },
        remove_product_qty_lines: function(origin_lines, product_list){
            var self = this;
            var success = true;
            var removed_products = [];
            if(origin_lines.length <= 0){
                return {
                    lines: origin_lines,
                    success: false,
                    removed_products: removed_products,
                }
            }
            var lines = self.check_and_clone_orderlines(origin_lines);

            product_list.forEach(function(product){
                for(var idx = 0 ; idx < lines.length && product.quantity > 0 ; idx++){
                    if(lines[idx].quantity > 0 && product.product_ids.includes(lines[idx].product.id)){
                        if(lines[idx].quantity >= product.quantity){
                            lines[idx].quantity -= product.quantity;
                            lines[idx].quantityStr = '' + lines[idx].quantity;
                            removed_products.push({
                                product_id: lines[idx].product.id,
                                quantity: product.quantity
                            });
                            product.quantity = 0;
                        }
                        else{
                            //case less than
                            removed_products.push({
                                product_id: lines[idx].product.id,
                                quantity: lines[idx].quantity
                            });
                            product.quantity -= lines[idx].quantity;
                            lines[idx].quantity = 0.0;
                            lines[idx].quantityStr = '' + 0.0;
                        }
                    }
                }
                if(product.quantity > 0){
                    success = false;
                }
            });
            return {
                lines: lines,
                success: success,
                removed_products: removed_products,
            };
        },
        get_domain_product_ids: function(domain, exclude_domain=false, promotion=false){
            var product_ids = [];
            if(domain.condition_product == 'brand' && domain.target_id in this.pos.db.product_by_brand_id)
                product_ids = this.pos.db.product_by_brand_id[domain.target_id].product_ids;
            else if(domain.condition_product == 'category' && domain.target_id in this.pos.db.product_by_categ_id)
                product_ids = this.pos.db.product_by_categ_id[domain.target_id].product_ids;
            else if((domain.condition_product == 'dept' || domain.condition_product == 'sub_dept')
                && domain.target_id in this.pos.db.product_by_dept_id)
                product_ids = this.pos.db.product_by_dept_id[domain.target_id].product_ids;
            else if(domain.condition_product == 'manual')
                product_ids = domain.condition_manual_product;
            else if(domain.condition_product == 'all'){
                this.get_orderlines().forEach(function(line){
                    if(line.promotion == promotion && !product_ids.includes(line.product.id))
                        product_ids.push(line.product.id)
                });
            }

            if(product_ids.length > 0 && exclude_domain){
                if(exclude_domain.exclude_condition_product == 'brand' && exclude_domain.exclude_target_id in this.pos.db.product_by_brand_id)
                    product_ids = product_ids.filter((product_id) => !this.pos.db.product_by_brand_id[exclude_domain.exclude_target_id].product_ids.includes(product_id));
                else if(exclude_domain.exclude_condition_product == 'category' && exclude_domain.exclude_target_id in this.pos.db.product_by_categ_id)
                    product_ids = product_ids.filter((product_id) => !this.pos.db.product_by_categ_id[exclude_domain.exclude_target_id].product_ids.includes(product_id));
                else if((exclude_domain.exclude_condition_product == 'dept' || exclude_domain.exclude_condition_product == 'sub_dept')
                    && exclude_domain.exclude_target_id in this.pos.db.product_by_dept_id)
                    product_ids = product_ids.filter((product_id) => !this.pos.db.product_by_dept_id[exclude_domain.exclude_target_id].product_ids.includes(product_id));
                else if(exclude_domain.exclude_condition_product == 'manual')
                    product_ids = product_ids.filter((product_id) => !exclude_domain.exclude_condition_manual_product.includes(product_id));
            }

            return product_ids;
        },
        get_orderline_by_product_id: function(product_id, at_least_quantity=false, discount=false, exclude_tiers=undefined){
            var orderlines = this.orderlines.models;
            if(at_least_quantity && at_least_quantity > 0){
                orderlines = orderlines.filter((line)=> line.quantity >= at_least_quantity);
            }
            if(exclude_tiers && exclude_tiers.length > 0){
                orderlines = orderlines.filter(function(line){
                    for(var i = 0; i < line.tiers.length; i++){
                        for(var j = 0; j < exclude_tiers.length; j++){
                            var ex_tier = exclude_tiers[j];
                            if(ex_tier.start_tier <= line.tiers[i] && line.tiers[i] <= ex_tier.end_tier){
                                return false;
                            }
                        }
                    }
                    return true;
                });
            }
            for(var i = 0; i < orderlines.length; i++){
                var line = orderlines[i];
                if(line.product.id === product_id && !line.promotion){
                    if(discount){
                        var discount_amount = discount.amount;
                        if(discount.is_percent){
                            discount_amount = (line.price * discount_amount) / 100;
                            if(discount.max_discount
                            && discount.max_discount > 0 && discount_amount > discount.max_discount){
                                discount_amount = discount.max_discount;
                            }
                        }
                        if(discount_amount <= line.price - (line.prorate_amount/line.quantity)){
                            return line;
                        }
                    }
                    else
                        return line;
                }
            }
            return false;
        },
        get_promotion_line_by_product_id: function(product_id, promotion_id, condition_id){
            var orderlines = this.orderlines.models;
            for(var i = 0; i < orderlines.length; i++){
                if(orderlines[i].product.id === product_id
                    && orderlines[i].promotion
                    && orderlines[i].promotion_id == promotion_id
                    && orderlines[i].promotion_condition_id == condition_id){
                    return orderlines[i];
                }
            }
            return false;
        },
        convert_product_into_orderline: function(product_lines){
            var orderline = [];
            product_lines.forEach(function(product_line){
                orderline.push({
                    product: product_line.product,
                    product_id: product_line.product.id,
                    price: product_line.price || product_line.product.price,
                    quantity: product_line.quantity,
                    qty: product_line.quantity,
                })
            });
            return orderline;
        },
        get_product_ids_by_quantity_and_discount: function(origin_lines, target_quantity, discount, sort = undefined){
            var self = this;
            if(origin_lines.length == 0)
                return {success:false};

            var lines = self.check_and_clone_orderlines(origin_lines);

            if(sort && ['asc', 'desc'].includes(sort)){
                lines = lines.sort((a, b) => {
                    if(sort == 'asc')
                        return a.price - b.price;
                    else
                        return b.price - a.price
                });
            }

            var product_ids = [];
            var total_price = 0;
            var total_discount = 0;
            for(var idx = 0; idx < lines.length && target_quantity > 0; idx++){
                var line = lines[idx];
                var discount_amount = discount.amount / line.quantity;
                if(discount.is_percent){
                    discount_amount = (line.price * discount_amount) / 100;
                    if(discount.max_discount && discount.max_discount > 0 && discount_amount > discount.max_discount)
                        discount_amount = discount.max_discount;
                }
                if(line.quantity > 0 && line.price - (line.prorate_amount/line.quantity) >= discount_amount){
                    if(target_quantity > line.quantity){
                        product_ids.push({
                            line_id: line.id,
                            product_id: line.product.id,
                            quantity:  line.quantity,
                            price: line.price,
                        });
                        total_price += (line.price * line.quantity) - line.prorate_amount;
                        total_discount += discount_amount * line.quantity;
                        target_quantity -= line.quantity;
                        line.quantity = 0;
                        line.qty = 0;
                    }
                    else{
                        product_ids.push({
                            line_id: line.id,
                            product_id: line.product.id,
                            quantity:  target_quantity,
                            price: line.price
                        });
                        total_price += (line.price * target_quantity) - line.prorate_amount;
                        total_discount += discount_amount * target_quantity;
                        line.quantity -= target_quantity,
                        line.qty-= target_quantity,
                        target_quantity = 0;
                    }
                }
            }
            return {
                product_ids: product_ids,
                success: target_quantity == 0,
                lines: lines,
                total_price: total_price,
                total_discount: total_discount,
            }
        },
        add_discount_with_prorate: function(lines, discount_amount, is_percent, time = 1, promotion_detail = {}){
            /*
                promotion_detail must be dict, if promotion_detail exist mean not manual promotion
                promotion detail has second prorate
            */
            var extras = {
                promotion: true,
                prorate_amount: 0.0,
                prorate_amount_exclude: 0.0,
                prorate_vat: 0.0,
                promotion_name: 'ส่วนลด',
                reward_type: 'discount',
            };
            extras = _.extend(extras, promotion_detail);
            var tier = false;

            if(extras.promotion_id && extras.promotion_condition_id){
                tier = this.pos.db.promotion_by_id[extras.promotion_id].tier;
                extras.promotion_name = this.get_promotion_line_name(extras.promotion_id, extras.promotion_condition_id);
                extras.is_manual_discount = false;
            }

            var promotion_product_id = this.pos.config.promotion_discount_product_id[0];
            var pro_product_id = this.pos.db.product_by_id[promotion_product_id];


            var line_wo_discount = lines.filter((line)=>line.promotion == false);
            var total_prorate = {
                amount: 0.0,
                amount_exclude: 0.0,
                vat: 0.0,
            };
            var line = undefined;
            var total_discount_w_tax = 0, total_discount_wo_tax = 0, taxes_id = [];
            var accumulated_prorate = 0;
            for(var round = 0; round < time; round++){
                var total_amount = 0;
                line_wo_discount.forEach(function(line){
                    total_amount += (line.price * line.quantity) -line.prorate_amount;
                });
                if(is_percent){//on step promotion
                    discount_amount = (total_amount * discount_amount)/100;
                }
                for(var idx = 0; idx < lines.length ; idx++){
                    line = lines[idx];

                    //found then add prorate to that line
                    var subtotal = (line.quantity * line.price) - line.prorate_amount;
                    /*
                    var is_lastline = idx === lines.length - 1;
                    if (is_lastline){
                        var prorate_parm = discount_amount - accumulated_prorate;
                    }else{
                        var prorate_parm = discount_amount * (subtotal/total_amount);
                    }
                    */

                    var prorate = line.get_all_prices_by_subtotal(
                        discount_amount * (subtotal/total_amount)
                        ,line.product
                    );
                    accumulated_prorate = accumulated_prorate + prorate.priceWithTax;
                    line.prorate_amount += prorate.priceWithTax;
                    line.prorate_amount_exclude += prorate.priceWithoutTax;
                    line.prorate_vat += prorate.tax;

                    line.prorate_ids.push(_.extend({
                        prorate_amount : prorate.priceWithTax,
                        prorate_amount_exclude: prorate.priceWithoutTax,
                        prorate_vat: prorate.tax,
                        is_manual_discount: true,
                    }, promotion_detail));

                    if(promotion_detail.second_prorate){
                        line.prorate_amount_2 += prorate.priceWithTax;
                        line.prorate_amount_exclude_2 += prorate.priceWithoutTax;
                        line.prorate_vat_2 += prorate.tax;
                    }

                    if(tier){
                        if(!(line.tiers instanceof Array))
                           line.tiers = [];

                        if(!line.tiers.includes(tier))
                            line.tiers.push(tier);
                    }
                    if(prorate.priceWithTax == prorate.priceWithoutTax)
                        total_discount_wo_tax += prorate.priceWithTax;
                    else{
                        total_discount_w_tax += prorate.priceWithTax;
                        taxes_id = _.union(taxes_id, line.product.taxes_id);
                    }

                }
            }

            if(total_discount_w_tax > 0){
                //prepare reward data
                var product_pro_discount = _.recursiveDeepCopy(pro_product_id);
                product_pro_discount.display_name = product_pro_discount.name = extras.promotion_name;

                product_pro_discount.taxes_id = taxes_id;
                this.add_product(product_pro_discount, {
                    price: (-1) * total_discount_w_tax,
                    quantity: 1,
                    extras: extras,
                    multi_line: true,
                });
            }

            if(total_discount_wo_tax > 0){
                //prepare reward data
                var product_pro_discount = _.recursiveDeepCopy(pro_product_id);
                product_pro_discount.display_name = product_pro_discount.name = extras.promotion_name;

                this.add_product(product_pro_discount, {
                    price: (-1) * total_discount_wo_tax,
                    quantity: 1,
                    extras: extras,
                    multi_line: true,
                });
            }
        },
        add_promotion_to_order: function(promotion_id, promotion_condition_id, time = 1, product_ids = []){
            var self = this;
            var promotion_product_id = this.pos.config.promotion_discount_product_id[0];
            var product_by_id = this.pos.db.product_by_id;
            var pro_product_id = product_by_id[promotion_product_id];

            var promotion = self.pos.db.promotion_by_id[promotion_id];
            var condition = self.pos.db.promotion_condition_by_id[promotion_condition_id];

            var promotion_type = promotion.promotion_type;
            var reward_type = promotion.reward_type;
            var is_best_deal = promotion.is_best_deal;
            var tier = promotion.tier;
            var apply_with_coupon = promotion.apply_with_coupon;

            var reward_amount = condition.reward_amount;

            var extras = {
                promotion: true,
                promotion_id: promotion.id,
                promotion_type: promotion.promotion_type,
                reward_type: reward_type,
                promotion_condition_id: condition.id,
                prorate_amount: 0.0,
                prorate_amount_exclude: 0.0,
                prorate_vat: 0.0,
                prorate_amount_2: 0.0,
                prorate_amount_exclude_2: 0.0,
                prorate_vat_2: 0.0,
                tiers: [tier],
            };

            if(reward_type == 'discount'){
                var product_taxes_ids = [];
                //find line and add prorate
                var is_percent = condition.reward_discount_percentage;
                var max_discount = condition.reward_max_discount;

                var exclude_tier = [];
                if(promotion.is_exclude_tier && _.isArray(promotion.exclude_tier_ids)
                && promotion.exclude_tier_ids.length > 0){
                    promotion.exclude_tier_ids.forEach(function(tier_id){
                        var tier = self.pos.db.tier_by_id[tier_id];
                        if(tier)
                            exclude_tier.push({
                                start_tier: tier.start_tier,
                                end_tier: tier.end_tier,
                            });
                    });
                }

                if(condition.is_select_product_discount){
                    if(product_ids.length > 0){
                        time = 0;
                        product_ids.forEach(function(item){
                            var line;
                            if(item.line_id){
                                line = self.get_orderlines().find( line => line.id == item.line_id);
                            }
                            else{
                                line = self.get_orderline_by_product_id(
                                    item.product_id, item.quantity,{
                                        amount: reward_amount,
                                        is_percent: is_percent,
                                        max_discount: max_discount,
                                    },
                                    exclude_tier,
                                );
                            }
                            if(line){
                                var discount_amount = reward_amount;
                                if(is_percent){
                                    discount_amount = line.price * discount_amount / 100;
                                    if(max_discount && max_discount > 0 && discount_amount > max_discount)
                                        discount_amount = max_discount;
                                }
                                /*  line A, price 20 Baht, qty 4, prorate 2 Baht
                                    to discount quantity 2, new discount = 2 Baht per product

                                    line A, price 20 Baht, qty 4,
                                            prorate 2 Baht (old) + (2 Baht (new prorate) + 2 Baht (new prorate))
                                    line B promotion line, price -2 Baht, qty 2 --line B on bottom */

                                var product = product_by_id[item.product_id];
                                discount_amount = line.get_all_prices_by_subtotal(discount_amount, product_by_id[item.product_id]);

                                // add tier to line A
                                if(!(line.tiers instanceof Array))
                                    line.tiers = [];

                                if(!line.tiers.includes(tier))
                                    line.tiers.push(tier);

                                var prorate_id = {
                                    promotion_id: promotion.id,
                                    promotion_condition_id: condition.id,
                                    prorate_amount : discount_amount.priceWithTax,
                                    prorate_amount_exclude: discount_amount.priceWithoutTax,
                                    prorate_vat: discount_amount.tax,
                                };

                                for(var i = 0; i < item.quantity; i++){
                                    line.prorate_amount += discount_amount.priceWithTax;
                                    line.prorate_amount_exclude += discount_amount.priceWithoutTax;
                                    line.prorate_vat += discount_amount.tax;
                                    line.prorate_ids.push(prorate_id);

                                }

                                //for discount tax checking
                                product.taxes_id.forEach(function(tax_id){
                                    if(!product_taxes_ids.includes(tax_id)){
                                        product_taxes_ids.push(tax_id);
                                    }
                                });
                                time += item.quantity;
                            }
                        });
                    }
                    else{
                        reward_amount = 0;
                    }

                    //prepare reward data
                    var product_pro_discount = _.recursiveDeepCopy(pro_product_id);
                    product_pro_discount.display_name = product_pro_discount.name = self.get_promotion_line_name(promotion.id, condition.id);
                    product_pro_discount.taxes_id = product_taxes_ids;
                    extras.promotion_name = product_pro_discount.name;

                    //add reward data
                    if(reward_amount){
                        self.add_product(product_pro_discount, {
                            price: (-1) * reward_amount,
                            quantity: time,
                            extras: extras,
                            multi_line: true,
                        });
                    }
                }
                else{
                    var parameters = [
                        'price', reward_type, is_best_deal,
                        self.get_orderlines(), {
                            condition_product: condition.condition_product,
                            condition_apply_id: condition.condition_apply_id,
                            condition_manual_product: condition.condition_manual_product
                        }
                    ];

                    if(condition.is_exclude_product)
                        parameters.push({
                            exclude_condition_product: condition.exclude_condition_product,
                            exclude_condition_apply_id: condition.exclude_condition_apply_id,
                            exclude_condition_manual_product: condition.exclude_condition_manual_product
                        });
                    else
                        parameters.push(false);

                    //exclude tiers
                    if(exclude_tier.length > 0)
                        parameters.push(exclude_tier);
                    else
                        parameters.push(false);

                    //calculate prorate
                    var calculated = self.calculate_sub.apply(self, parameters);
                    var focus_lines = self.get_orderlines().filter((line) => calculated.line_ids.includes(line.id))
                    var promotion_detail = {
                        promotion_id: promotion.id,
                        promotion_condition_id: condition.id,
                    };
                    self.add_discount_with_prorate(focus_lines, reward_amount, is_percent, time, promotion_detail);
                }
            }
            else if(apply_with_coupon == 'reward' && product_ids.length > 0){
                product_ids.forEach(function(product){
                    var coupon = product_by_id[product.product_id];
                    for(var i = 0; i < product.quantity * time ; i++){
                        self.add_product(coupon, {
                            quantity: (-1),
                            extras: _.extend(extras, {
                                line_coupon: 'reward_coupon'
                            }),
                            multi_line: true,
                        });
                    }
                });
            }
            else if(reward_type == 'product' && product_ids.length > 0){
                //find line and minus qty then add product line and proline
                // before: A:3  pro A 2: free A 1
                // after : A:2 A_free:1 Pro_A:-1
                // make sure it not use multi-line **

                product_ids.forEach(function(reward){
                    //find the same promotion in orderline
                    var extras_temp = _.recursiveDeepCopy(extras);

                    if(!reward.force_add){
                        var a_free = self.get_promotion_line_by_product_id(reward.product_id, promotion.id, condition.id);
                        var pro_a = self.get_promotion_line_by_product_id(promotion_product_id, promotion.id, condition.id);
                        var line = self.get_orderline_by_product_id(reward.product_id);
                        if(a_free && pro_a && line && line.quantity - reward.quantity >= 0){
                            line.set_quantity(line.quantity - reward.quantity);

                            a_free.set_quantity(a_free.quantity + reward.quantity);
                            pro_a.set_quantity(pro_a.quantity + (-1) * reward.quantity);
                        }
                        else if(line && reward.quantity > 0){
                            line.set_quantity(line.quantity - reward.quantity);

                            var product_a_free = self.pos.db.product_by_id[reward.product_id];
                            self.add_product(product_a_free, {
                                quantity: reward.quantity,
                                extras: extras_temp,
                                multi_line: true,
                            });

                            var product_pro_a = _.recursiveDeepCopy(product_a_free);
                            product_pro_a.id =  promotion_product_id;
                            product_pro_a.taxes_id = product_a_free.taxes_id;
                            product_pro_a.display_name = product_pro_a.name = self.get_promotion_line_name(promotion.id, condition.id, reward.product_id);

                            extras_temp.free_product_id = reward.product_id;
                            extras_temp.promotion_name = product_pro_a.name;

                            self.add_product(product_pro_a, {
                                price: product_a_free.price,
                                quantity: (-1) * reward.quantity,
                                extras: extras_temp,
                                multi_line: true,
                            });
                        }
                        if(line && line.quantity == 0)
                            self.remove_orderline(line);
                    }
                    else{
                        //force add
                        extras_temp.force_add = true;
                        var product_a_free = self.pos.db.product_by_id[reward.product_id];
                        self.add_product(product_a_free, {
                            quantity: reward.quantity,
                            extras: extras_temp,
                            multi_line: true,
                        });

                        var product_pro_a = _.recursiveDeepCopy(product_a_free);
                        product_pro_a.id =  promotion_product_id;
                        product_pro_a.taxes_id = product_a_free.taxes_id;
                        product_pro_a.display_name = product_pro_a.name = self.get_promotion_line_name(promotion.id, condition.id, reward.product_id);

                        extras_temp.free_product_id = reward.product_id;
                        extras_temp.promotion_name = product_pro_a.name;

                        self.add_product(product_pro_a, {
                            price: product_a_free.price,
                            quantity: (-1) * reward.quantity,
                            extras: extras_temp,
                            multi_line: true,
                        });
                    }
                });

            }
        },
        pos_promotion_threshold_compare: function(amount, target){
            if(amount >= target * this.pos.system_parameter_pos_promotion_threshold)
                return true;
            return false;
        },
        possible_promotion: function(origin_lines, targets, time=1, exclude_tiers=false){
            var self = this;
            var fail = {success: false};

            if(origin_lines.length <= 0){
                return fail;
            }
            var lines = self.check_and_clone_orderlines(origin_lines);

            var product_ids = undefined;

            //filter promotion line and exclude tier
            lines = lines.filter(function(line){
                if(line.tiers && exclude_tiers){
                    for(var i = 0; i < line.tiers.length; i++){
                        for(var j = 0; j < exclude_tiers.length; j++){
                            var ex_tier = exclude_tiers[j];
                            if(ex_tier.start_tier <= line.tiers[i] && line.tiers[i] <= ex_tier.end_tier){
                                return false;
                            }
                        }
                    }
                }
                return !line.promotion && !self.pos.db.product_coupon_ids.includes(line.product.id);
            });

            lines = lines.sort((a,b) => (a.price != b.price)?a.price - b.price: a.product.id - b.product.id);

            var total = 0;
            var total_reward_price = 0;

            if(targets.reward_target){
                if(!targets.reward_target.skip_reward && !targets.is_free_as_same_pid){
                    if(targets.reward_target.is_discount){
                        var discount_amount = targets.reward_target.amount;

                        if(targets.reward_target.is_select_product_discount){
                            // make sure to sort lines from the cheapest price
                            var result = self.get_product_ids_by_quantity_and_discount(
                                lines.filter((line) => targets.reward_target.product_ids.includes(line.product.id)), time, {
                                    amount: discount_amount,
                                    is_percent: targets.reward_target.is_percent,
                                    max_discount: targets.reward_target.max_discount,
                                }
                            );

                            // cannot find all discount product
                            if(!result.success)
                                return fail;

                            product_ids = result.product_ids;
                            total_reward_price = result.total_discount;
                        }
                        else{
                            if(targets.reward_target.is_percent){
                                var discount_domain = undefined;

                                discount_amount = lines.filter(function(line){
                                    return targets.condition_target.product_ids.includes(line.product.id);
                                }).reduce(function(sum, line){
                                    return sum + (line.price * line.quantity) - line.prorate_amount;
                                },0) * discount_amount/100;

                                if(targets.reward_target.max_discount
                                && targets.reward_target.max_discount > 0 && discount_amount > targets.reward_target.max_discount){
                                    discount_amount = targets.reward_target.max_discount;
                                }
                            }
                            total_reward_price = discount_amount * time;
                        }
                        //total = total - total_reward_price;
                    }
                    else{
                        var product_by_id = self.pos.db.product_by_id;
                        var to_remove_product_ids = [];
                        if(targets.reward_target.reward_mapping_product_qty_ids){
                            targets.reward_target.reward_mapping_product_qty_ids.forEach(function(product_qty){
                                to_remove_product_ids.push({
                                    product_ids: [product_qty.product_id_int],
                                    quantity: product_qty.qty * time,
                                });
                            });
                        }
                        else{
                            to_remove_product_ids.push({
                                product_ids: targets.reward_target.product_ids,
                                quantity: targets.reward_target.amount * time,
                            });
                        }

                        var result = self.remove_product_qty_lines(lines, to_remove_product_ids);
                        if(!result.success){
                            return fail;
                        }
                        else{
                            lines = result.lines;

                            //for free_product_ids
                            product_ids = result.removed_products;
                            total_reward_price = product_ids.reduce(function(sum, item){
                                return sum + product_by_id[item.product_id].price * item.quantity;
                            }, 0);
                        }
                    }
                }
            }
            else return fail;

            if(targets.is_free_as_same_pid){
                var product_by_id = self.pos.db.product_by_id;
                product_ids = []
                if(targets.reward_target.amount){
                    targets.condition_target.product_ids.forEach(function(product_id){
                        var sum = lines.filter((line) =>  product_id == line.product.id).reduce(function(sum, line){
                            return sum + line.quantity;
                        }, 0);
                        var time = parseInt(sum/targets.target_amount_same_pid)
                        if(targets.condition_bill_limit && time > targets.condition_bill_limit){
                            time = targets.condition_bill_limit;
                        }

                        if(time){
                            product_ids.push({
                                product_id: product_id,
                                quantity: time,
                            })
                        }
                    });
                }
                if(product_ids.length == 0){
                    return fail;
                }
                total_reward_price = product_ids.reduce(function(sum, item){
                    return sum + product_by_id[item.product_id].price * item.quantity;
                }, 0);
            }
            else if(targets.condition_target){
                if(targets.condition_target.is_price){
                    //filter for interested product line
                    lines = lines.filter((line) =>  targets.condition_target.product_ids.includes(line.product.id));
                    total = lines.reduce(function(sum, line){
                        return sum + (line.price * line.quantity) - line.prorate_amount;
                    }, total);

                    // not reach to promotion
                    if(total < targets.condition_target.amount * time){
                        return fail;
                    }
                }
                else{
                    var result = undefined;
                    var to_remove_product_ids = [];

                    if(targets.condition_target.condition_mapping_product_qty_ids){
                        targets.condition_target.condition_mapping_product_qty_ids.forEach(function(product_qty){
                            to_remove_product_ids.push({
                                product_ids: [product_qty.product_id_int],
                                quantity: product_qty.qty * time,
                            });
                        });
                    }
                    else{
                        to_remove_product_ids.push({
                            product_ids: targets.condition_target.product_ids,
                            quantity: targets.condition_target.amount * time,
                        });
                    }
                    var result = self.remove_product_qty_lines(lines, to_remove_product_ids);
                    if(!result.success){
                        return _.extend(fail, {removed_products: result.removed_products});
                    }
                }
            }
            else return fail;

            /*if(time == 1 && ){
                return _.extend(fail, {
                    pass_threshold: true,
                });
            }

            if(time == 1 && self.pos_promotion_threshold_compare(total, targets.condition_target.amount)){
                return _.extend(fail, {
                    pass_threshold: true,
                });
            }


            if(try_condition_of_free_product){
                return _.extend(fail, {
                    free_product_ids: targets.reward_target.product_ids,
                });
            }*/

            return {
                success: true,
                product_ids: product_ids,
                total_reward_price: total_reward_price,
            };
        },
        apply_promotions: function(){
            var self = this;
            var order = this;//in model order
            if(order.is_calculated_promotion){
                order.reverse_promotions();
            }
            //sort reward_product_ids to be on the last order
            //sort conpon line to stay after reward
            var reward_lines = [];
            var other_lines = [];
            var coupon = {
                lines: [],
                ids: {},
            };

            order.orderlines.models.forEach(function(line){
                if(line.product.is_coupon){
                    if(!(line.product.id in coupon.ids)){
                        coupon.ids[line.product.id] = [];
                    }

                    coupon.ids[line.product.id].push({
                        product_id: line.product.id,
                        line: line,
                        remain_quantity: line.quantity,
                    });

                    coupon.lines.push(line);
                }
                else if(self.pos.db.reward_product_ids.includes(line.product.id))
                    reward_lines.push(line);
                else
                    other_lines.push(line);
            });
            order.orderlines.models = (other_lines.concat(reward_lines)).concat(coupon.lines);

            var available_tiers = self.calculate_promotion(coupon);
            var applied_promotions = [];
            var diff = 0;
            var promotion_by_id = self.pos.db.promotion_by_id;
            var condition_by_id = self.pos.db.promotion_condition_by_id;

            var result_promotions = [];
            var require_free_product = [];
            var pass_threshold = [];

            //load killed promotion from order
            var killed_promotions = order.killed_promotions;

            _.keys(available_tiers).sort().forEach(function(tier){
                available_tiers[tier].forEach(function(priority, priority_num){
                    var success = undefined;
                    var calulated_promotions = [];
                    priority.forEach(function(promotion, priority_idx){
                        var promotion_id = promotion_by_id[promotion.promotion_id];
                        var promotion_type = promotion_id.promotion_type;
                        var condition_type = promotion_id.condition_type;
                        var reward_type = promotion_id.reward_type;
                        var is_best_deal = promotion_id.is_best_deal;
                        var apply_with_coupon = promotion_id.apply_with_coupon;

                        if(!promotion_id.active)
                            return;

                        //exclude tiers
                        var exclude_tier = false;
                        if(promotion_id.is_exclude_tier && _.isArray(promotion_id.exclude_tier_ids)
                        && promotion_id.exclude_tier_ids.length > 0){
                            exclude_tier = [];
                            promotion_id.exclude_tier_ids.forEach(function(tier_id){
                                var tier = self.pos.db.tier_by_id[tier_id];
                                if(tier)
                                    exclude_tier.push({
                                        start_tier: tier.start_tier,
                                        end_tier: tier.end_tier,
                                    });
                            });
                        }

                        var conditions = [condition_by_id[promotion.promotion_condition_id]];

                        if(promotion_type == 'step'){
                            conditions = promotion_id.condition_ids;
                        }

                        var killed_index = killed_promotions.findIndex(function(item){
                            if(item.promotion_id == promotion_id.id
                            && conditions.find((condition)=> item.condition_id == condition.id)){
                                return true;
                            }
                            else
                                return false;
                        });

                        var promotion_obj = {
                            promotion_id: promotion_id.id,
                            name: promotion_id.promotion_name,
                            selected: true,
                        };

                        if(killed_index != -1){
                            calulated_promotions.push(_.extend(promotion_obj, {
                                promotion_condition_id: killed_promotions[killed_index].condition_id,
                                killed: true,
                            }));
                            // stop doing loop forEach
                            return;
                        }

                        var time = promotion.target;
                        diff += time;

                        var applied_promotion = {success:false};
                        var condition = undefined;

                        var orderline = order.orderlines.models.filter((line)=>!line.product.is_coupon);
                        if(!is_best_deal){
                            orderline = orderline.filter(line => !line.product.is_best_deal_promotion);
                        }

                        for(var idx = 0; idx < conditions.length && !applied_promotion.success; idx++){
                            time = promotion.target;
                            condition = conditions[idx];
                            if(condition.inactive)
                                continue;

                            var condition_amount = condition.condition_amount;

                            var apply_to_reward = condition.apply_to_reward;
                            var is_free_as_same_pid = condition.is_free_as_same_pid;

                            var reward_amount = condition.reward_amount;

                            var condition_domain = [{
                                condition_product: condition.condition_product,
                                target_id: condition.condition_apply_id,
                                condition_manual_product: condition.condition_manual_product,
                            }];

                            if(condition.is_exclude_product)
                                condition_domain.push({
                                    exclude_condition_product: condition.exclude_condition_product,
                                    exclude_target_id: condition.exclude_condition_apply_id,
                                    exclude_condition_manual_product: condition.exclude_condition_manual_product,
                                });

                            var reward_domain = [{
                                condition_product: condition.reward_product,
                                target_id: condition.reward_apply_id,
                                condition_manual_product: condition.reward_manual_product,
                            }];

                            if(condition.is_exclude_reward)
                                reward_domain.push({
                                    exclude_condition_product: condition.exclude_reward_product,
                                    exclude_target_id: condition.exclude_reward_apply_id,
                                    exclude_condition_manual_product: condition.exclude_reward_manual_product,
                                });

                            var targets = {
                                condition_target: {},
                                reward_target: {
                                    amount: reward_amount,
                                    is_discount: (reward_type=='discount')?true:false,
                                    is_percent: condition.reward_discount_percentage,
                                    max_discount: condition.reward_max_discount,
                                    is_select_product_discount: condition.is_select_product_discount,
                                },
                                is_free_as_same_pid: is_free_as_same_pid,
                                target_amount_same_pid: condition_amount + reward_amount,
                                condition_bill_limit: promotion_id.promotion_type == 'step'?1:conditions.condition_bill_limit|| 0,
                            };

                            if(condition.is_condition_mapping_qty && condition.condition_mapping_product_qty_ids instanceof Array
                            && condition.condition_mapping_product_qty_ids.length > 0){
                                targets.condition_target = {
                                    condition_mapping_product_qty_ids: condition.condition_mapping_product_qty_ids,
                                    is_price: false, //there is no condition price on mapping promotions
                                }
                            }
                            else{
                                targets.condition_target = {
                                    product_ids: self.get_domain_product_ids.apply(self, condition_domain),
                                    amount: condition_amount,
                                    is_price: (condition_type=='price')?true:false,
                                };
                            }

                            if(apply_to_reward){
                                if(condition.is_condition_mapping_qty && condition.condition_mapping_product_qty_ids){
                                    targets.reward_target.product_ids = condition.condition_mapping_product_qty_ids.reduce(function(result, item){
                                        if(item.product_id_int)
                                            return result.concat(item.product_id_int);
                                        else
                                            return result;
                                    }, []);
                                }
                                else{
                                    targets.reward_target.product_ids = targets.condition_target.product_ids;
                                }
                            }
                            else{
                                // give coupon
                                if(apply_with_coupon == 'reward' && condition.reward_coupon_product_id instanceof Array){
                                    targets.reward_target.skip_reward = true;
                                }
                                else if(condition.is_reward_mapping_qty && condition.reward_mapping_product_qty_ids instanceof Array
                                && condition.reward_mapping_product_qty_ids.length > 0){
                                    targets.reward_target.reward_mapping_product_qty_ids = condition.reward_mapping_product_qty_ids;
                                    targets.reward_target.is_discount = false; //there is no condition price on mapping promotions
                                }
                                else{
                                    targets.reward_target.product_ids = self.get_domain_product_ids.apply(self, reward_domain);
                                }
                            }

                            // count coupon in order lines
                            var coupon_amount = undefined;
                            if(apply_with_coupon == 'condition' && condition.condition_coupon_product_id){
                                if(condition.condition_coupon_product_id[0] in coupon.ids){
                                    coupon_amount = coupon.ids[condition.condition_coupon_product_id[0]].reduce(function(sum, coupon){
                                        return  sum + coupon.remain_quantity;
                                    }, 0);
                                }
                            }

                            while(time > 0 && !applied_promotion.success){
                                var skip = false;
                                // !coupon_amount for case false, undefined and zero
                                if(apply_with_coupon == 'condition' && (!coupon_amount || coupon_amount < time) )
                                    skip = true;

                                if(!skip)
                                    applied_promotion = self.possible_promotion(orderline, targets, time, exclude_tier);

                                time--;
                            }
                        }

                        promotion_obj.promotion_condition_id = condition.id;
                        if(applied_promotion.success){
                            time++;

                            var discount_to_display = undefined;
                            //give reward as coupon
                            if(apply_with_coupon == 'reward' && condition.reward_coupon_product_id instanceof Array){
                                applied_promotion.product_ids = [{
                                    product_id: condition.reward_coupon_product_id[0],
                                    quantity: reward_amount,
                                }];
                                discount_to_display = time;
                            }
                            else{
                                discount_to_display = self.pos.chrome.screens.payment.format_currency(-applied_promotion.total_reward_price);
                            }

                            promotion_obj = _.extend(promotion_obj, {
                                amount: discount_to_display,
                                priority_idx: priority_idx,
                                max_discount: applied_promotion.total_reward_price,
                                condition: condition,
                                time: time,
                                apply_with_coupon: apply_with_coupon,
                                condition_coupon_id: (apply_with_coupon == 'condition')?condition.condition_coupon_product_id[0]:false,
                                product_ids: applied_promotion.product_ids,
                                selected: false,
                            });

                            calulated_promotions.push(promotion_obj);

                            // find the best
                            if(!success || applied_promotion.total_reward_price > success.max_discount)
                                success = promotion_obj;
                        }
                        else{
                            //try on only condition
                            targets.reward_target.skip_reward = true;
                            if(promotion_id.reward_type === 'product'){
                                if(targets.is_free_as_same_pid){
                                    targets.target_amount_same_pid = targets.condition_target.amount;
                                }
                                applied_promotion = self.possible_promotion(orderline, targets, 1, exclude_tier);
                                if(applied_promotion.success){
                                    require_free_product.push(promotion_obj);
                                }
                            }
                            if(!applied_promotion.success){
                                //try with pass_threshold
                                if(targets.is_free_as_same_pid){
                                    targets.target_amount_same_pid = parseInt(targets.target_amount_same_pid * self.pos.system_parameter_pos_promotion_threshold);
                                }
                                else{
                                    targets.condition_target.amount = parseInt(targets.condition_target.amount * self.pos.system_parameter_pos_promotion_threshold);
                                }

                                applied_promotion = self.possible_promotion(orderline, targets, 1, exclude_tier);
                                if(applied_promotion.success){
                                    pass_threshold.push(promotion_obj);
                                }
                                else if(targets.condition_target.condition_mapping_product_qty_ids && applied_promotion.removed_products){
                                    var target_condition_amount = condition.condition_mapping_product_qty_ids.reduce(((sum, p) => sum + p.qty), 0);
                                    var total_condition_amount = applied_promotion.removed_products.reduce((sum, p) => sum + p.quantity, 0);
                                    if(total_condition_amount > target_condition_amount * self.pos.system_parameter_pos_promotion_threshold){
                                        pass_threshold.push(promotion_obj);
                                    }
                                }

                            }

                        }
                    });
                    // use the best
                    if(success){
                        var condition = success.condition;
                        self.add_promotion_to_order(condition.promotion_id[0], condition.id, success.time, success.product_ids);

                        if(success.apply_with_coupon == 'condition' && success.condition_coupon_id){
                            var time = success.time;
                            _.values(coupon.ids[success.condition_coupon_id]).forEach(function(coupon){
                                if(coupon.remain_quantity > 0 && time > 0){
                                    if(coupon.remain_quantity > time){
                                        coupon.remain_quantity -= time;
                                        time = 0;
                                    }
                                    else{
                                        time -= coupon.remain_quantity;
                                        coupon.remain_quantity = 0;
                                    }
                                }
                            });
                        }

                        var apply_no = success.time;
                        diff -= apply_no;
                        if(apply_no > 0){
                            //there is target to apply
                            var apply_pro = _.recursiveDeepCopy(priority[success.priority_idx]);
                            apply_pro.qty = apply_no;
                            applied_promotions.push(apply_pro);
                        }

                        success.selected = true;
                    }
                    if(calulated_promotions.length > 0){
                        result_promotions.push({
                            tier: tier,
                            priority: priority_num,
                            promotions: calulated_promotions,
                        });
                    }
                });
            });

            //remove unused coupon to removed list
            _.values(coupon.ids).forEach(function(coupons){
                coupons.forEach(function(coupon){
                    var line = coupon.line;
                    if(coupon.remain_quantity == 0){
                        //used all coupon skip to next
                        return;
                    }
                    order.removed_coupons[coupon.product_id] = [];
                    if(coupon.remain_quantity == line.quantity){
                        order.removed_coupons[coupon.product_id].push({
                            product_id: coupon.product_id,
                            quantity: coupon.remain_quantity,
                            coupon_barcode: line.coupon_barcode,
                            multi_coupon_id: line.multi_coupon_id,
                        });
                        if(line.remove_timeout)
                            clearTimeout(line.remove_timeout);
                        order.remove_orderline(line);
                    }
                    else{
                        order.removed_coupons[coupon.product_id].push({
                            product_id: coupon.product_id,
                            quantity: coupon.remain_quantity,
                            coupon_barcode: coupon.coupon_barcode,
                            multi_coupon_id: line.multi_coupon_id,
                        });
                        line.quantity = parseInt(line.quantity - coupon.remain_quantity);
                        line.quantityStr = '' + line.quantity;
                    }
                });
            });
            //sort promotion line to bottom
            var promotion_lines = [];
            other_lines = [];
            order.orderlines.models.forEach(function(line){
                if(line.promotion)
                    promotion_lines.push(line);
                else
                    other_lines.push(line);
            });
            order.orderlines.models = other_lines.concat(promotion_lines);

            this.is_calculated_promotion  = true;

            this.save_to_db();
            return {
                diff: diff,
                applied_promotions: applied_promotions,
                result_promotions: result_promotions,
                require_free_product: require_free_product,
                pass_threshold: pass_threshold,
            }
        },
        //for printing
        export_for_printing: function(){
            var self = this;
            var receipt = _super_order.prototype.export_for_printing.call(self);
            // reorder orderline
            var promotion_product_id = self.pos.config.promotion_discount_product_id[0];

            var line_by_product_id = {};
            var line_promotion_by_product_id = {};
            var line_discount_by_condition_id = {};
            var line_reward_coupons = [];
            receipt.orderlines.forEach(function(line){
                var product_id = line.product_id;
                if(product_id == promotion_product_id){
                    if(line.reward_type == 'product'){
                        product_id = line.free_product_id;
                        if(product_id in line_promotion_by_product_id){
                            line_promotion_by_product_id[product_id].quantity += line.quantity;
                        }
                        else{
                            line_promotion_by_product_id[product_id] = line;
                        }
                    }
                    else{
                        if(line.promotion_condition_id in line_discount_by_condition_id){
                            line_discount_by_condition_id[line.promotion_condition_id].price += line.price; //?
                        }
                        else{
                            line_discount_by_condition_id[line.promotion_condition_id] = line;
                        }
                    }
                }
                else{
                    if(line.line_coupon && line.line_coupon == 'reward_coupon'){
                        line_reward_coupons.push(line);
                    }
                    else if(product_id in line_by_product_id){
                        line_by_product_id[product_id].quantity += line.quantity;
                    }
                    else{
                        line_by_product_id[product_id] = line;
                    }
                }
            });

            var orderlines = [];
            _.values(line_by_product_id).sort((a,b) => a.product_id - b.product_id).forEach(function(line){
                orderlines.push(line);
                if(line.product_id in line_promotion_by_product_id){
                    orderlines.push(line_promotion_by_product_id[line.product_id]);
                }
            });

            var discount_lines = _.values(line_discount_by_condition_id);
            var total_discount = 0.0;
            discount_lines.forEach(function(line){
                total_discount += line.price;
            });

            var sub_total = 0.0;
            orderlines.forEach(function(line){
                sub_total += line.quantity * line.price;
            });

            receipt.orderlines = orderlines;
            receipt.discount_lines = discount_lines;
            receipt.sub_total = sub_total;
            receipt.total_discount = total_discount;

            receipt.reward_coupons = line_reward_coupons;

            return receipt;
        },
        get_subtotal_without_discount: function(){
            var promotion_by_id = this.pos.db.promotion_by_id;
            var sub_total = 0.0;
            var orderlines = this.get_orderlines();
            orderlines.forEach(function(line){
                if(line.promotion && line.reward_type == 'discount'){
                    return;
                }
                else{
                    sub_total += line.price * line.quantity;
                }
            });
            return sub_total;
        },
    });

    var _super_orderline = models.Orderline;
    models.Orderline = models.Orderline.extend({
        initialize: function (attr, options) {
            this.promotion = false;
            this.promotion_id = false;
            this.promotion_type = false;
            this.promotion_name = false;
            this.reward_type = false;
            this.promotion_condition_id = false;
            this.free_product_id = false;
            this.prorate_amount = 0.0;
            this.prorate_amount_exclude = 0.0;
            this.prorate_vat = 0.0;
            this.prorate_amount_2 = 0.0;
            this.prorate_amount_exclude_2 = 0.0;
            this.prorate_vat_2 = 0.0;
            this.tiers = [];
            this.prorate_ids = [];
            _super_orderline.prototype.initialize.call(this, attr, options);
        },
        init_from_JSON: function (json) {
            _super_orderline.prototype.init_from_JSON.call(this, json);
            this.promotion = json.promotion;
            this.promotion_id = json.promotion_id;
            this.promotion_type = json.promotion_type;
            this.reward_type = json.reward_type;
            this.promotion_condition_id = json.promotion_condition_id;
            this.free_product_id = json.free_product_id;
            this.prorate_amount = json.prorate_amount;
            this.prorate_amount_exclude = json.prorate_amount_exclude;
            this.prorate_vat = json.prorate_vat;
            this.prorate_amount_2 = json.prorate_amount_2;
            this.prorate_amount_exclude_2 = json.prorate_amount_exclude_2;
            this.prorate_vat_2 = json.prorate_vat_2;
            this.tiers = json.tiers;

            this.force_add = json.force_add;
            //coupon
            this.line_coupon = json.line_coupon;
            this.coupon_barcode = json.coupon_barcode;
            this.multi_coupon_id = json.multi_coupon_id;

            //prorate_ids
            this.prorate_ids = [];
            for (var i = 0; json.prorate_ids && i < json.prorate_ids.length; i++) {
                if(json.prorate_ids[i].id){
                    for(var key in json.prorate_ids[i]){
                        if(!(["promotion_id", "promotion_condition_id",
                            "prorate_amount", "prorate_amount_exclude", "prorate_vat"].includes(key))){
                            delete json.prorate_ids[i][key]
                        }
                        else if(key.search("id") >=0){
                            json.prorate_ids[i][key] = json.prorate_ids[i][key][0]
                        }
                    }
                    this.prorate_ids.push(json.prorate_ids[i]);
                }
                else{
                    this.prorate_ids.push(json.prorate_ids[i][2]);
                }
            }

            if(this.promotion && this.product.id == this.pos.config.promotion_discount_product_id[0]){
                if(json.promotion_name){
                    this.promotion_name  = json.promotion_name;
                }
                else{
                    this.promotion_name  = this.order.get_promotion_line_name(this.promotion_id, this.promotion_condition_id);;
                }
                var new_product = _.recursiveDeepCopy(this.product);
                new_product.display_name = new_product.name = this.promotion_name;
                this.product = new_product;
            }
        },
        export_as_JSON: function () {
            var json = _super_orderline.prototype.export_as_JSON.call(this);
            json.promotion = this.promotion;
            json.promotion_id = this.promotion_id;
            json.promotion_name = this.promotion_name;
            json.promotion_type = this.promotion_type;
            json.reward_type = this.reward_type;
            json.promotion_condition_id = this.promotion_condition_id;
            json.free_product_id = this.free_product_id;
            json.prorate_amount = this.prorate_amount;
            json.prorate_amount_exclude = this.prorate_amount_exclude;
            json.prorate_vat = this.prorate_vat;
            json.prorate_amount_2 = this.prorate_amount_2;
            json.prorate_amount_exclude_2 = this.prorate_amount_exclude_2;
            json.prorate_vat_2 = this.prorate_vat_2;
            json.tiers = this.tiers;

            json.force_add = this.force_add;
            //coupon
            json.line_coupon = this.line_coupon;
            json.coupon_barcode = this.coupon_barcode;
            json.multi_coupon_id = this.multi_coupon_id;

            //prorate_ids
            json.prorate_ids = [];
            for (var i = 0; i < this.prorate_ids.length; i++) {
                json.prorate_ids.push([0, 0,  this.prorate_ids[i]]);
            }

            //for calcurate promotion
            json.price = this.price;
            json.quantity = this.quantity;
            return json;
        },
        set_quantity: function(quantity) {
            var screen_name = this.pos.gui.get_current_screen();
            if (screen_name == 'products' && this.promotion)
                return;
            else{
                var screen_name = this.pos.gui.get_current_screen();
                if (screen_name == 'products'
                    && !this.order.on_reverse_promotion_process && this.order.is_calculated_promotion) {
                    var selected_line = this;
                    this.order.reverse_promotions();
                    this.order.select_orderline(selected_line);
                    _super_orderline.prototype.set_quantity.call(this,quantity);
                }
                else{
                    _super_orderline.prototype.set_quantity.call(this,quantity);
                }

            }
        },
        export_for_printing: function(){
            var receipt = _super_orderline.prototype.export_for_printing.call(this);
//            list value return from super
//            quantity:           this.get_quantity(),
//            unit_name:          this.get_unit().name,
//            price:              this.get_unit_display_price(),
//            discount:           this.get_discount(),
//            product_name:       this.get_product().display_name,
//            product_name_wrapped: this.generate_wrapped_product_name(),
//            price_display :     this.get_display_price(),
//            price_with_tax :    this.get_price_with_tax(),
//            price_without_tax:  this.get_price_without_tax(),
//            tax:                this.get_tax(),
//            product_description:      this.get_product().description,
//            product_description_sale: this.get_product().description_sale,

            //product detail

            var product = this.get_product();
            receipt.product_id = product.id;
            receipt.barcode = product.barcode;
            receipt.iface_line_tax_included = this.check_tax(product);
            receipt.flag_best_deal = product.is_best_deal_promotion;

            //promotion detail
            receipt.promotion = this.promotion;
            receipt.promotion_id = this.promotion_id;
            receipt.promotion_name = this.promotion_name;
            receipt.promotion_type = this.promotion_type;
            receipt.free_product_id = this.free_product_id;
            receipt.reward_type = this.reward_type;
            receipt.promotion_condition_id = this.promotion_condition_id;
            receipt.prorate_amount = this.prorate_amount;
            receipt.prorate_amount_exclude = this.prorate_amount_exclude;
            receipt.prorate_vat = this.prorate_vat;

            //promotion coupon reward
            receipt.product_is_coupon = product.is_coupon;
            receipt.line_coupon = this.line_coupon;
            if(this.line_coupon == 'reward_coupon'){
                if(product.coupon_type == 'single'){
                    receipt.coupon_barcode = this.product.barcode;
                    receipt.coupon_barcode_image_base64 = this.product.coupon_barcode_image_base64;
                }
                else if(product.coupon_type == 'multi'){
                    receipt.line_coupon = this.line_coupon;
                    receipt.coupon_barcode = this.coupon_barcode;
                    receipt.coupon_barcode_image_base64 = this.coupon_barcode_image_base64;
                }
                receipt.coupon_image_base64 = product.image_base64;
            }

            receipt.product_coupon_type = product.coupon_type;
            if(product.description){
                receipt.product_description = product.description.split('\n').join('<br/>');
            }

            return receipt;
        },
        get_display_coupon_barcode: function(){
            if(this.product.is_coupon && (this.coupon_barcode || this.product.barcode))
                return '[' + (this.coupon_barcode || this.product.barcode) + ']';
            else
                return '';
        },
        get_html_coupon_barcode: function(){
            var coupon_barcode = this.get_display_coupon_barcode();
            if(coupon_barcode.length){
                coupon_barcode = '<span style="margin-right:1px;">'+ coupon_barcode+'</span>'
            }
            return coupon_barcode;
        },
    });

});