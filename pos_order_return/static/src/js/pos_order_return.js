/* Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>) */
/* See LICENSE file for full copyright and licensing details. */
/* License URL : <https://store.webkul.com/license.html/> */
odoo.define('pos_order_return.pos_order_return', function (require) {
"use strict";
	var pos_orders = require('pos_orders.pos_orders');
	var core = require('web.core');
	var gui = require('point_of_sale.gui');
	var QWeb = core.qweb;
	var screens = require('point_of_sale.screens');
	var models = require('point_of_sale.models');
	var PopupWidget = require('point_of_sale.popups');
	var _t = core._t;
	var SuperOrder = models.Order;
	var SuperOrderline =  models.Orderline.prototype;
	var SuperPosModel = models.PosModel.prototype;
	var formats = require('web.formats');
	var SuperPaymentScreen = screens.PaymentScreenWidget.prototype;

	var utils = require('web.utils');
	var time = require('web.time');
	var round_pr = utils.round_precision;
    var round_di = utils.round_decimals;


	models.load_fields('product.product','not_returnable');

    models.load_models([{
        model: 'return.reason',
        fields:['id','name'],
        domain: [['model','=', 'pos.order']],
        loaded: function(self, return_reason){
            self.db.return_reason = return_reason;
            self.db.return_reason_by_id = {};
            return_reason.forEach(function(reason){
                self.db.return_reason_by_id[reason.id] = reason;
            });
        }
    }]);

	var MyMessagePopup = PopupWidget.extend({
		template: 'MyMessagePopup'
	});
	gui.define_popup({ name: 'my_message', widget: MyMessagePopup });

	var OrderReturnPopup = PopupWidget.extend({
		template: 'OrderReturnPopup',
		events: {
			'click .button.cancel':  'click_cancel',
			'click #complete_return':  'click_complete_return',
			'click #return_order':  'click_return_order',
		},
		click_return_order: function(event, force_validation = false){
            var self = this;
			var all = $('.return_qty');
			var return_dict = {};
			var return_entries_ok = true;
            self.options.is_partial_return = false;
            var all_zero = true;

            var remaining_line = {};

			$.each(all, function(index, value){
				var input_element = $(value).find('input');
				var line_quantity_remaining = parseFloat(input_element.attr('line-qty-remaining'));
				var line_id = parseFloat(input_element.attr('line-id'));
				var qty_input = parseFloat(input_element.val());
				var line_promotion = (input_element.attr('promotion')  === 'true');

				if(!$.isNumeric(qty_input) || qty_input > line_quantity_remaining
				    || (!line_promotion &&  qty_input < 0 || qty_input != parseInt(qty_input)) ){
					return_entries_ok = false;
					input_element.addClass("border-required-field");
				}
				else{
				    input_element.removeClass("border-required-field");
				}

				if(qty_input == 0 && line_quantity_remaining != 0 && !self.options.is_partial_return)
					self.options.is_partial_return = true;
				else if(line_promotion || qty_input > 0){
                    return_dict[line_id] = qty_input;
					if(line_quantity_remaining != qty_input  && !self.options.is_partial_return)
						self.options.is_partial_return = true;
					else if(!self.options.is_partial_return)
						self.options.is_partial_return = false;
				}

                var new_remaining_qty = line_quantity_remaining - qty_input;
				if(self.options.page_type == 'return'){
				    remaining_line[line_id] = new_remaining_qty;
                    var line_free_product = (input_element.attr('is-free-product')  === 'true');
                    if(line_free_product){
                        //recover free line to dic
				        var line_free_id= parseFloat(input_element.attr('line-free-id'));
                        return_dict[line_free_id] = (-1)*qty_input;
                    }
				}
				if(qty_input != 0)
				    all_zero = false;
			});

			var return_reason_box = $('.return_reason_selection_box');
			var return_reason_id = return_reason_box.val();
			if(return_reason_id == ''){
                return_entries_ok = false;
                return_reason_box.addClass("border-required-field");
            }
            else{
                return_reason_box.removeClass("border-required-field");
            }

            if(all_zero){
                $.each(all, function(index, value){
                    $(value).find('input').addClass("border-required-field");
                });
                return_entries_ok = false;
            }

            var amount_tender = 0;
            var total_previous_cash = 0.0;
            var cash_found = false;
            return_entries_ok && self.options.order.statement_ids.forEach(function(statement_id){
                var statement = self.pos.db.statement_by_id[statement_id];
                var cashregister = null;

                if(statement){
                    for ( var i = 0; i < self.pos.cashregisters.length; i++ ) {
                        if ( self.pos.cashregisters[i].journal_id[0] === statement.journal_id[0] ){
                            cashregister = self.pos.cashregisters[i];
                            break;
                        }
                    }
                    if( (cashregister && cashregister.journal.type == 'cash')
                    || (self.options.page_type == 'return' &&  statement.credit_card_no != '' && statement.credit_card_no.length > 0
                        && statement.credit_card_type == 'QKBN' ) ){
                        total_previous_cash += statement.amount - statement.line_amount_returned;
                        if(!cash_found){
                            cash_found = true;
                            amount_tender++;
                        }
                    }
                    else{
                        amount_tender++;
                    }
                }
            });



            if(return_entries_ok && self.options.is_partial_return){
                var total_amount_return = 0.0;
                Object.keys(return_dict).forEach(function(line_id){
                    var line = self.pos.db.line_by_id[line_id];
                    total_amount_return += line.price_unit * parseFloat(return_dict[line_id])
                });

                if(amount_tender > 1){
                    if(total_previous_cash <= 0){
                        self.gui.show_popup('alert', {
                            'title': 'Alert',
                            'body': 'ไม่สามารถทำรายการคืนบางส่วนได้ จะต้องทำคืนทั้งหมดเท่านั้น'
                        });
                        return_entries_ok = false;
                    }
                    else if(total_amount_return > total_previous_cash){
                        self.gui.show_popup('alert', {
                            'title': 'Alert',
                            'body': 'ไม่สามารถทำรายการคืนบางส่วนได้ เนื่องจาก ยอดที่คืน('
                                + self.chrome.screens.payment.format_currency(total_amount_return)
                                + ') เกิน ยอดเงิดสด '
                                + self.chrome.screens.payment.format_currency(total_previous_cash)
                        });
                        return_entries_ok = false;
                    }
                }
            }

            if(!force_validation && self.options.page_type == 'return'
            && return_entries_ok && !self.check_return_promotion(self, remaining_line)){
                return_entries_ok = false;
            }
			if(return_entries_ok){
                if(Object.keys(return_dict).length > 0){
                    var refund_order = self.create_return_order(return_dict, return_reason_id, amount_tender);
                    self.pos.set_order(refund_order);
                    self.gui.show_screen('payment');
                }
                else{
                    self.$("input").css("background-color","#ff8888;");
                    setTimeout(function(){
                        self.$("input").css("background-color","");
                    },100);
                    setTimeout(function(){
                        self.$("input").css("background-color","#ff8888;");
                    },200);
                    setTimeout(function(){
                        self.$("input").css("background-color","");
                    },300);
                    setTimeout(function(){
                        self.$("input").css("background-color","#ff8888;");
                    },400);
                    setTimeout(function(){
                        self.$("input").css("background-color","");
                    },500);
                }
			}
		},
		check_return_promotion: function(self, remaining_line){
            var order_lines = [];
            var free_lines = [];
            //check currently promotion
            var promotion_by_id = self.pos.db.promotion_by_id;
            var condition_by_id = self.pos.db.promotion_condition_by_id;
            var line_by_id = self.pos.db.line_by_id;
            //temp order
            var order = self.pos.get_order();

            var is_remain_free_product_line = false;
            Object.keys(remaining_line).forEach(function(line_id){
                var new_remaining_qty = remaining_line[line_id];
                if(new_remaining_qty > 0){
                    var line = _.recursiveDeepCopy(line_by_id[line_id]);
                    line.quantity = new_remaining_qty;
                    line.product = {id: line.product_id[0]}
                    if(self.options.free_line_ids.includes(line.id))
                        free_lines.push(line);
                    else
                        order_lines.push(line);
                }
            });

            free_lines.length > 0 && free_lines.forEach(function(free_line){
                var promotion = promotion_by_id[free_line.promotion_id[0]];
                var condition = condition_by_id[free_line.promotion_condition_id[0]];

                var condition_target = {};
                if(promotion.promotion_type == 'mapping' && condition.mapping_product_qty_ids){
                    condition_target.mapping_product_qty_ids = condition.mapping_product_qty_ids;
                }
                else{
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

                    condition_target.product_ids = order.get_domain_product_ids.apply(order, condition_domain);
                    condition_target.amount = condition.condition_amount;
                }

                var time = Math.ceil(free_line.quantity/condition.reward_amount);
                var target_amount = time;
                var result = {success:false};
                while(!result.success && time > 0){
                    if(promotion.condition_type == 'price'){
                        var total = order_lines.filter(function(line){
                            return condition_target.product_ids.includes(line.product.id);
                        }).reduce(function(sum, line){
                            var remaining_qty = qty - line_qty_returned;
                            var remaining_prorate = line.prorate_amount * (remaining_qty / qty);
                            return sum + (line.price_unit * line.quantity)
                                - ((line.quantity/remaining_qty) * remaining_prorate);
                        }, 0);
                        // reach to promotion
                        if(total >= condition_target.amount * time){
                            result.success = true;
                        }
                    }
                    else{
                        var result = undefined;
                        var to_remove_product_ids = [];
                        if(condition_target.mapping_product_qty_ids){
                            condition_target.mapping_product_qty_ids.forEach(function(product_qty){
                                to_remove_product_ids.push({
                                    product_ids: [product_qty.product_id[0]],
                                    quantity: product_qty.qty * time,
                                });
                            });
                        }
                        else{
                            to_remove_product_ids = [{
                                product_ids: condition_target.product_ids,
                                quantity: condition_target.amount * time,
                            }];
                        }
                        var result = order.remove_product_qty_lines(order_lines, to_remove_product_ids);
                    }
                    time--;
                }
                if(result.success){
                    time++;
                    order_lines = result.lines;

                }
                free_line.qty = free_line.quantity - (condition.reward_amount * time);
            });

            free_lines = free_lines.filter((line) => line.qty > 0);
            if(free_lines.length > 0){
                var product_by_id = self.pos.db.product_by_id;
                var str_text = free_lines.reduce(function(text, orderline){
                    return text + '<li>' + product_by_id[orderline.product_id[0]].name + ' จำนวน '+ orderline.qty + 'ชิ้น'+ '</li>';
                }, '');
                self.pos.gui.show_popup('confirm_promotion', {
                    'title': 'Alert',
                    'body': '<div style=\'text-align: center;\'>คุณยังไม่ได้คืนสินค้าของแถม</div><br/>'
                        + '<ul style=\'font-weight:400;\'>'+ str_text  +'</ul>'
                        + '<br/><div style=\'text-align: center;\'>กดยืนยันเพื่อทำต่อ</div>' ,
                    confirm: function() {
                        self.click_return_order(self ,'confirm');
                    },
                });
                return false;
            }
            return true;
		},
		create_return_order: function(return_dict, return_reason_id, amount_tender){
			var self = this;
			var order = self.options.order;
			var orderlines = self.options.orderlines;
			var current_order = self.pos.get_order();
			var order_statement_ids = order.statement_ids;

            var refund_order = self.pos.get_order();
            if(refund_order.get_orderlines().length > 0){
                self.gui.show_popup('alert', {
                    'title': 'Alert',
                    'body': 'Order is not empty'
                });
                return;
            }
            //make it temporary
            refund_order.temporary = true;

            var old_order = self.pos.db.order_by_id[order.id];

            if(self.options.approver){
                refund_order.approver_id = self.options.approver.id;
                refund_order.approve_datetime = self.options.approver.datetime;
            }

            refund_order.return_reason_id = return_reason_id;
            refund_order.inv_no_old = old_order.inv_no;
            refund_order.date_order_old =  moment(old_order.date_order).format('DD.MM.YYYY');
            refund_order.brand_id_old =  self.pos.db.branch_by_id[old_order.branch_id[0]].branch_id;
            refund_order.previous_invoice_id = old_order.invoice_id;
            refund_order.the_one_card_no = old_order.the_one_card_no;

            refund_order.is_void_order = false;
            refund_order.is_return_order = false;
            if(self.options.page_type == 'void'){
                refund_order.is_void_order = true;
                refund_order.is_return_order = false;
            }
            else if(self.options.page_type == 'return'){
                refund_order.is_void_order = false;
                refund_order.is_return_order = true;
            }

            refund_order.set_client(self.pos.db.get_partner_by_id(order.partner_id[0]));

            //add payment statements methods
            refund_order.previous_journals = {};
            refund_order.previous_payments = [];
            refund_order.previous_payment_by_id = {};
            var allow_tender = 1;
            if(!self.options.is_partial_return){
                allow_tender = amount_tender;
            }
            var cash_cashregister = self.pos.cashregisters.filter((cashregister)=> cashregister.journal.type == 'cash')[0];
            var statement_list = [];
            order_statement_ids.forEach(function(statement_id){
                var statement = self.pos.db.statement_by_id[statement_id];
                if(statement){
                    var is_credit_card = false;
                    if(statement.credit_card_no != '' && statement.approve_code != ''
                        && statement.credit_card_no.length > 0 && statement.approve_code.length > 0){
                        is_credit_card = true;
                    }
                    statement.is_credit_card = is_credit_card;

                    var cashregister = null;
                    if(statement.credit_card_type == 'QKBN' || ((statement.t1cc_barcode != "") && (refund_order.is_return_order))){
                        cashregister = cash_cashregister
                    }
                    else{
                        for ( var i = 0; i < self.pos.cashregisters.length; i++ ) {
                            if ( self.pos.cashregisters[i].journal_id[0] === statement.journal_id[0] ){
                                cashregister = self.pos.cashregisters[i];
                                break;
                            }
                        }

                    }
                    statement.cashregister = cashregister;
                    statement_list.push(statement);
                }
            });
            statement_list.sort(function(a, b){
                var a_type = a.cashregister.journal.type;
                var b_type = b.cashregister.journal.type;
                if(a_type == b_type)
                    return 0;
                else if (a_type == 'cash')
                    return -1;
                else //case other and b_type = case
                    return 1;
            });

            statement_list.forEach(function(statement){
                var journal_id = statement.journal_id[0];

                if(refund_order.is_return_order && statement.is_credit_card
                && statement.credit_card_type == 'QKBN'){
                    statement.cashregister = cash_cashregister;
                    statement.is_credit_card = false;
                    statement.journal_id = cash_cashregister.journal_id;
                    statement.credit_card_no = '';
                    statement.credit_card_no_encrypt = '';
                    statement.credit_card_type = '';
                    statement.approve_code = '';
                }
                // console.log(statement.amount);
                //set the remaining amount
                statement.amount -= statement.line_amount_returned;
                if (statement.t1cc_barcode != "") { 
                    allow_tender += 1;
                }
                if(statement.amount <= 0 || allow_tender == 0){
                    return;
                }
                //make sure that there is one cash statement
                refund_order.previous_journals[journal_id] = statement;
                refund_order.previous_payments.push(statement);
                refund_order.previous_payment_by_id[statement.id] = statement;
                allow_tender--;
            });
            //sort cash on the last
            refund_order.previous_payments.sort(function(a, b){
                var a_type = a.cashregister.journal.type;
                var b_type = b.cashregister.journal.type;
                if(a_type == b_type)
                    return 0;
                else if (a_type == 'cash')
                    return 1;
                else
                    return -1;
            })

            var promotion_product_id = this.pos.config.promotion_discount_product_id[0];
            Object.keys(return_dict).forEach(function(line_id){
                var line = self.pos.db.line_by_id[line_id];
                var extras = {
                    is_return: true,
                    prorate_amount: line.prorate_amount,
                    prorate_amount_exclude: line.prorate_amount_exclude,
                    prorate_vat: line.prorate_vat,
                };
                if(line.promotion){
                    extras.promotion = line.promotion;
                    extras.promotion_id = line.promotion_id[0];
                    extras.promotion_type = line.promotion_type;
                    extras.reward_type = line.reward_type;
                    extras.promotion_condition_id = line.promotion_condition_id[0];
                    extras.promotion_name = line.promotion_name;
                    extras.free_product_id = line.free_product_id[0];
                    if(line.line_coupon)
                        extras.line_coupon = line.line_coupon;
                    if(line.multi_coupon_id){
                        extras.multi_coupon_id = line.multi_coupon_id[0];
                        extras.coupon_barcode = line.multi_coupon_barcode;
                        if(line.multi_coupon_barcode in self.pos.db.multi_coupon_by_barcode){
                            extras.coupon_barcode_image_base64 = self.pos.db.multi_coupon_by_barcode[line.multi_coupon_barcode].barcode_image_base64;
                        }
                        else{
                            extras.coupon_barcode_image_base64 = self.pos.db.get_barcode_image(line.multi_coupon_barcode);
                        }
                    }
                }
                var product = undefined;
                if(line.product_id[0] == promotion_product_id){
                    product = _.recursiveDeepCopy(self.pos.db.get_product_by_id(line.product_id[0]));
                    product.display_name = product.name = line.promotion_name;
                }
                else{
                    product = self.pos.db.get_product_by_id(line.product_id[0]);
                }

                //prorate recalculate
                var new_qty = return_dict[line_id];
                if(new_qty > 0 && line.qty != new_qty){
                    var new_ratio = (new_qty / line.qty);
                    extras.prorate_amount = extras.prorate_amount * new_ratio;
                    extras.prorate_amount_exclude = extras.prorate_amount_exclude * new_ratio;
                    extras.prorate_vat = extras.prorate_vat * new_ratio;
                }

                if(line.line_coupon == 'reward_coupon'){
                    refund_order.add_product(
                        product,
                        {
                            quantity: new_qty,
                            price: line.price_unit,
                            discount: line.discount,
                            extras: extras,
                            multi_line: true,
                        }
                    );
                }
                else{
                    refund_order.add_product(
                        product,
                        {
                            quantity: -1*parseFloat(new_qty),
                            price: line.price_unit,
                            discount: line.discount,
                            extras: extras,
                            multi_line: true,
                        }
                    );
                }

                refund_order.selected_orderline.original_line_id = line.id;
            });

            if(refund_order.is_return_order){
                var total_return_discount_promotion = 0.0;
                refund_order.get_orderlines().forEach(function(line){
                    total_return_discount_promotion += line.prorate_amount;
                });
                if(total_return_discount_promotion > 0){
                    var product_pro_discount = _.clone(self.pos.db.product_by_id[promotion_product_id]);
                    var extras = {
                        promotion: true,
                        reward_type: 'discount',
                        prorate_amount: 0.0,
                        prorate_amount_exclude: 0.0,
                        prorate_vat: 0.0,
                        promotion_name: 'คืนส่วนลดโปรโมชั่น',
                    };

                    refund_order.add_product(product_pro_discount, {
                        price: (-1)*total_return_discount_promotion,
                        quantity: -1,
                        extras: extras,
                        multi_line: true,
                    });
                }
            }

            if(refund_order.is_void_order){
                refund_order.change_rounding = old_order.change_rounding * -1;
            }
            else{
                refund_order.change_rounding = old_order.change_rounding;
            }

            if(self.options.is_partial_return){
                refund_order.return_status = 'Partially-Returned';
            }else{
                refund_order.return_status = 'Fully-Returned';
            }
            refund_order.return_order_id = order.id;
            return refund_order;
		},
		click_complete_return: function(){
			var self = this;
			var all = $('.return_qty');
			$.each(all, function(index, value){
				var line_quantity_remaining = parseFloat($(value).find('input').attr('line-qty-remaining'));
				$(value).find('input').val(line_quantity_remaining);
			});
		},
		show: function(options){
			options = options || {};
			var self = this;
			this._super(options);
			this.orderlines = options.orderlines || [];
			this.return_reason = this.pos.db.return_reason || [];
			this.page_type = options.page_type;
			this.renderElement();
			var all_input = this.$('.return_qty > input');
			if(options.page_type == 'void'){
                this.$('.void_return_type').html('Void');
			    this.$('#complete_return').hide();
			    this.click_complete_return();
			    all_input.prop('disabled', true);
			    all_input.prop('readonly', true);
			}
			else if(options.page_type == 'return'){
			    this.$('.void_return_type').html('Return');
			    if(options.include_promotion){
                    this.$('#complete_return').hide();
			        this.click_complete_return();
                    all_input.prop('disabled', true);
                    all_input.prop('readonly', true);
			    }
			    else{
                    this.$('#complete_return').show();
                    all_input.prop('disabled', false);
                    all_input.prop('readonly', false);
			    }
			}
		},
	});
	gui.define_popup({ name: 'return_products_popup', widget: OrderReturnPopup });

	screens.ClientListScreenWidget.include({
		show: function(){
	        var self = this;
			var current_order = self.pos.get_order();
			self._super();
			if(current_order != null && (current_order.is_void_order || current_order.is_return_order)){
				self.gui.back();
			}
		}
	});

    screens.ActionpadWidget.include({
        change_page: function(self){
            //inherit from promotion
            var order = self.pos.get_order();
            if(order.is_void_order || order.is_return_order){
                self.gui.show_screen('payment');
            }
            else{
                //go to promotion page
                this._super(self);
            }
        },
    });


    var paymentline_proto = models.Paymentline.prototype;
    models.Paymentline = models.Paymentline.extend({
        initialize: function(attributes, options) {
            var self = this;
            this.original_line_id = false;
            this.line_amount_returned = 0.0;
            paymentline_proto.initialize.call(this, attributes, options);
        },
        init_from_JSON: function(json){
            var self = this;
            this.original_line_id  = json.original_line_id;
            this.line_amount_returned = json.line_amount_returned;
            paymentline_proto.init_from_JSON.call(this, json);
        },
        export_as_JSON: function(){
            var self = this;
            var loaded = paymentline_proto.export_as_JSON.call(this);
            loaded.original_line_id  = this.original_line_id;
            loaded.line_amount_returned = this.line_amount_returned;
            return loaded;
        },
    });


	var SuperPaymentScreenWidget = screens.PaymentScreenWidget.prototype.payment_input
	screens.PaymentScreenWidget.include({
		events : _.extend({}, SuperPaymentScreen.events, {
            'click .button.cancel_refund_order': 'delete_return_order',
		}),
		delete_return_order: function(){
			$(".deleteorder-button").trigger("click");
		},
		click_back: function(){
            //inherit from promotion
            var order = this.pos.get_order();
            if(order.is_void_order || order.is_return_order){
                this.gui.show_screen('products');
            }
            else{
                //go to promotion page
                this._super();
            }
        },
		show:function(){
			var self = this;
			var order = self.pos.get_order();
            self._super();
			if(order && (order.is_void_order || order.is_return_order)){
			    var paymentmethods_container = this.$('.paymentmethods-container');
                paymentmethods_container.empty();
                var methods = this.render_paymentmethods();
                methods.appendTo(paymentmethods_container);
				this.el.querySelector('.payment-screen h1').textContent = order.is_void_order?'Void':'Refund';

                this.default_payment();

				self.$el.find('.button.cancel_refund_order').show();
				self.$el.find('.button.back').hide();
			}
			else{
				self.$el.find('.button.cancel_refund_order').hide();
				self.$el.find('.button.back').show();
			}
		},
        render_paymentlines: function(){
            var self = this;
            var order = self.pos.get_order();
            this._super();
            if(order.is_void_order || order.is_return_order){
                self.$el.find('.delete-button').hide();
            }
            else{
                self.$el.find('.delete-button').show();
            }
        },
        validate_order: function(force_validation){
            var self = this;
            var order = this.pos.get_order();
            if(order && (order.is_void_order || order.is_return_order)){
                force_validation = 'force_return';
            }
            this._super(force_validation);
        },
        order_is_valid: function(force_validation) {
            var self = this;
            var current_order = self.pos.get_order();
            if(current_order.is_void_order || current_order.is_return_order){
                var paymentlines = current_order.get_paymentlines();
                for(var idx = 0; idx < paymentlines.length ; idx++){
                    var paymentline = paymentlines[idx];

                    //only case return without promotion//case cash skip checking from the previous
                    if(current_order.is_return_order &&  !current_order.is_calculated_promotion
                        && paymentline.cashregister.journal.type == 'cash')
                        continue;

                    var previous_payment = current_order.previous_payment_by_id[paymentline.original_line_id];
                    if(previous_payment){
                        if(round_pr(paymentline.amount, 0.01) > round_pr(previous_payment.amount, 0.01)){
                            var currency_replace = " (" + self.pos.currency.name + ")";
                            if(previous_payment.is_credit_card){
                                self.gui.show_popup('alert', {
                                    'title': 'Invalid Payment line',
                                    'body': 'ห้ามคืนเกินยอด ' + previous_payment.amount
                                    + ' ของบัตรเครดิต ' + previous_payment.credit_card_no_encrypt,
                                });
                            }
                            else if(current_order.is_return_order && paymentline.cashregister.journal.type == 'cash'){
                                continue;
                            }
                            else{
                                self.gui.show_popup('alert', {
                                    'title': _t(''),
                                    'body': _t('Cannot return ') +
                                            previous_payment.journal_id[1].replace(currency_replace, '') +
                                            _t(' greater than ') + previous_payment.amount,
                                });
                            }
                            return false;
                        }
                    }
                    else{
                        self.gui.show_popup('alert', {
                            'title': _t('Invalid Payment line'),
                            'body': _t('Previous Payment line not found'),
                        });
                        return false;
                    }
                }
            }
            return this._super(force_validation);
        },
        finalize_validation: function(){
            var self = this;
            var order = self.pos.get_order();
            if(order.is_return_order && !order.is_calculated_promotion){
                var total_paid = order.get_total_paid();
                var total_with_tax = order.get_total_with_tax();
                if(total_paid != total_with_tax){
                    var change_rounding = Math.abs(round_pr(Math.abs(total_paid) - Math.abs(total_with_tax), 0.01))
                    order.change_rounding = change_rounding;
                }
            }
            this._super();
        },
        click_numpad: function(button) {
            var self = this;
			var order = self.pos.get_order()
		    if(order.is_void_order || order.is_return_order){
                return;
            }
            self._super(button);
        },
        payment_input: function(input) {
			var self = this;
			var order = self.pos.get_order()
		    if(order.is_void_order){
                return;
            }
			if(order.is_return_order){
			    return;
			    /*if(order.is_calculated_promotion || order.return_status == 'Fully-Returned'
			    || order.selected_paymentline === undefined){
                    return;
                }*/
                var newbuf = this.gui.numpad_input(this.inputbuffer, input, {'firstinput': this.firstinput});

                this.firstinput = (newbuf.length === 0);

                // popup block inputs to prevent sneak editing.
                if (this.gui.has_popup()) {
                    return;
                }

                if (newbuf !== this.inputbuffer) {
                    this.inputbuffer = newbuf;
                    var order = this.pos.get_order();
                    if (order.selected_paymentline) {
                        var amount = this.inputbuffer;
                        if (this.inputbuffer !== "-") {
                            amount = formats.parse_value(this.inputbuffer, {type: "float"}, 0.0);
                        }

                        var total_remain = order.get_total_remain();
                        if(total_remain > 0){
                            total_remain = round_di(total_remain + order.change_rounding, 2);
                        }
                        else if(total_remain < 0){
                            total_remain = 0;
                        }

                        if(order.selected_paymentline.original_line_id){
                            var previous_payment = order.previous_payment_by_id[order.selected_paymentline.original_line_id];
                            if(order.selected_paymentline.cashregister.journal.type != 'cash'){
                                if(previous_payment.is_credit_card){
                                    amount = previous_payment.amount;
                                }
                                else if (amount > previous_payment.amount){
                                    //case other tender (future)
                                    amount = previous_payment.amount;
                                }
                            }
                            if(previous_payment.is_credit_card && amount > total_remain){
                                //if the amount greater than subtotal reset to zero

                                this.gui.show_popup('alert', {
                                    'title': 'Alert',
                                    'body': 'ห้ามคืนเกินยอด ' + previous_payment.amount
                                    + ' ของบัตรเครดิต ' + previous_payment.credit_card_no_encrypt,
                                });
                                amount = 0;
                            }
                        }

                        if(amount > total_remain){
                            if(order.selected_paymentline.cashregister.journal.type == 'cash'){
                                amount = order.get_total_rounding(order.selected_paymentline.get_amount() + total_remain);
                            }
                            else{
                                amount = order.selected_paymentline.get_amount() + total_remain;
                            }
                        }

                        order.selected_paymentline.set_amount(amount);
                        this.inputbuffer = amount + '';
                        this.order_changes();
                        this.render_paymentlines();
                        this.$('.paymentline.selected .edit').text(this.format_currency_no_symbol(amount));
                    }
                }
                return;
            }
			else{
			    self._super(input);
			}
		},
        set_no_change: function() {
            var self = this;
            var order = self.pos.get_order();
            if(order.is_void_order){
                return;
            }
            if(order.is_return_order){
                return;
                /*if(order.is_calculated_promotion || order.return_status == 'Fully-Returned'
                || order.selected_paymentline === undefined){
                    return;
                }*/

                var amount = 0;
                var total_remain = order.get_total_remain();
                if(total_remain > 0){
                    total_remain = round_di(total_remain + order.change_rounding, 2);
                }
                else if(total_remain < 0){
                    total_remain = 0;
                }

                if(order.selected_paymentline.original_line_id){
                    var previous_payment = order.previous_payment_by_id[order.selected_paymentline.original_line_id];
                    amount = previous_payment.amount;

                    if(order.selected_paymentline.cashregister.journal.type == 'cash' ){
                        amount = order.get_total_rounding(order.selected_paymentline.get_amount() + total_remain);
                    }
                    else if(amount > total_remain){
                        amount = order.selected_paymentline.get_amount() + total_remain;
                    }
                }
                else{
                    amount = total_remain + order.selected_paymentline.amount;
                }


                order.selected_paymentline.set_amount(amount);
                self.order_changes();
                self.render_paymentlines();
                self.$('.paymentline.selected .edit').text(this.format_currency_no_symbol(amount));
                return;
            }
            else{
                self._super();
            }
        },
        render_paymentmethods: function() {
            var self = this;
            var order = this.pos.get_order();
            var old_cashregisters = this.pos.cashregisters;
            if(order.is_void_order || order.is_return_order){
                this.pos.cashregisters = [];
            }
            var methods = this._super();
            //restore back globel
            this.pos.cashregisters = old_cashregisters;
            return methods;
        },
        default_payment: function(){
            var self = this;
            var order = this.pos.get_order();
            var previous_payments = this.pos.get_order().previous_payments;
            // console.log('previous_payments',previous_payments);

            var total_with_tax = order.get_total_with_tax();
            var total_rounding = order.get_total_rounding(total_with_tax);

            var total_paid = 0.0;
            var cash_paymentline = undefined;
            previous_payments.forEach(function(previous_payment){
                if(order.get_due() == 0)
                    return;
                if((order.is_return_order && !order.is_void_order && order.return_status != 'Fully-Returned'
                && previous_payment.cashregister.journal.type != 'cash' && previous_payments.length > 1)
                || previous_payment.amount <= 0){
                    return;
                }
                order.add_paymentline(previous_payment.cashregister);
                if(previous_payment.cashregister.journal.type == 'cash'){
//                    var change_rounding = order.get_total_rounding(previous_payment.amount);
//                    previous_payment.amount = change_rounding;
                    cash_paymentline = order.selected_paymentline;
                }
                if (previous_payment.cashregister.journal.redeem_type_id) {
                    let is_t1cc = previous_payment.cashregister.journal.redeem_type_id.code === "T1CC";
                    let is_t1cp = previous_payment.cashregister.journal.redeem_type_id.code === "T1CP";
                    if (is_t1cc) {
                        order.selected_paymentline.t1cc_barcode = previous_payment.t1cc_barcode;
                    }
                    if (is_t1cp) {
                        order.selected_paymentline.t1cp_receipt_no = previous_payment.t1cp_receipt_no;
                        order.selected_paymentline.transactions = previous_payment.transactions;
                        order.selected_paymentline.api_to_be_cancelled = previous_payment.api_to_be_cancelled;
                        order.selected_paymentline.api_cancel_success = previous_payment.api_cancel_success;
                    }
                }
                order.selected_paymentline.original_line_id = previous_payment.id;
                if(previous_payment.is_credit_card){
                    order.selected_paymentline.credit_card_no = previous_payment.credit_card_no;
                    order.selected_paymentline.credit_card_no_encrypt = previous_payment.credit_card_no_encrypt;
                    order.selected_paymentline.credit_card_type = previous_payment.credit_card_type;
                    order.selected_paymentline.approve_code = (order.is_void_order)? previous_payment.approve_code: '';
                }
                if(order.is_void_order || order.return_status == 'Fully-Returned'){
                    // console.log('set amount')
                    order.selected_paymentline.set_amount(previous_payment.amount);
                }
                else{
                    if(order.selected_paymentline.cashregister.journal.type == 'cash'){
                        order.selected_paymentline.set_amount(order.get_total_rounding(order.get_due()));
                    }
                }
                total_paid += order.selected_paymentline.get_amount();
            });

            var remaining_amount = Math.abs(Math.abs(total_with_tax) - Math.abs(total_paid))
            if(remaining_amount == 0){
                order.change_rounding = 0;
            }

            if(order.is_return_order && order.is_paid_with_cash() && cash_paymentline){
//                total_with_tax - total_paid < 0.25
                var cash_due = order.get_due(cash_paymentline);
                if(cash_due){
                    var total_integer = Math.abs(parseInt(cash_due));
                    var total_decimal = Math.abs(Math.abs(cash_due) - Math.abs(total_integer));
                    var amount_total_rounding = 0.0;
                    if (total_decimal > 0.75){
                        amount_total_rounding = total_integer + 1.00;
                    }
                    else if (total_decimal > 0.50 && total_decimal < 0.75){
                        amount_total_rounding = total_integer + 0.75;
                    }
                    else if (total_decimal > 0.25 && total_decimal < 0.50){
                        amount_total_rounding = total_integer + 0.50;
                    }
                    else if (total_decimal > 0.00 && total_decimal < 0.25){
                        amount_total_rounding = total_integer + 0.25;
                    }
                    else{
                        amount_total_rounding = Math.abs(cash_due);
                    }
                    order.change_rounding = amount_total_rounding - cash_due;
                    cash_paymentline.set_amount(amount_total_rounding);
                }
            }

            //select first line
            order.select_paymentline(order.get_paymentlines()[0]);


            self.order_changes();
            self.render_paymentlines();
            order.save_to_db();
		},
	});

	screens.ProductScreenWidget.include({
		show: function(){
			var self = this;
			var current_order = self.pos.get_order();
			$("#cancel_refund_order").on("click", function(){
				$(".deleteorder-button").trigger("click");
			});
			this._super();
			if(current_order != null && (current_order.is_void_order || current_order.is_return_order)
			&& !current_order.is_exchange_order){
				$('.product').css("pointer-events","none");
				$('.product').css("opacity","0.4");
				$('.header-cell').css("pointer-events","none");
				$('.header-cell').css("opacity","0.4");
				$('#refund_order_notify').show();
				$('#cancel_refund_order').show();
				self.$('.numpad-backspace').css("pointer-events","none");
				self.$('.numpad').addClass('return_order_button');
				self.$('.numpad button').addClass('return_order_button');
				self.$('.button.set-customer').addClass('return_order_button');
				self.$('.all_orders').addClass('return_order_button');
			}
			else if(current_order != null && (current_order.is_void_order || current_order.is_return_order)
			&& current_order.is_exchange_order){
				$('.product').css("pointer-events","");
				$('.product').css("opacity","");
				$('.header-cell').css("pointer-events","");
				$('.header-cell').css("opacity","");
				$('#refund_order_notify').hide();
				$('#cancel_refund_order').hide();
				self.$('.numpad-backspace').css("pointer-events","");
				self.$('.numpad').removeClass('return_order_button');
				self.$('.numpad button').removeClass('return_order_button');
				self.$('.button.set-customer').addClass('return_order_button');
				self.$('.all_orders').addClass('return_order_button');
			}
			else{
				$('.product').css("pointer-events","");
				$('.product').css("opacity","");
				$('.header-cell').css("pointer-events","");
				$('.header-cell').css("opacity","");
				$('#refund_order_notify').hide();
				$('#cancel_refund_order').hide();
				self.$('.numpad-backspace').css("pointer-events","");
				self.$('.numpad').removeClass('return_order_button');
				self.$('.numpad button').removeClass('return_order_button');
				self.$('.button.set-customer').removeClass('return_order_button');
				self.$('.all_orders').removeClass('return_order_button');
			}
			if(current_order.is_void_order || current_order.is_return_order){
			    this.$('.t1c_in_product_class').prop('disabled', true);
			    this.$('.t1c_in_product_class').prop('readonly', true);
			}
            else{
                this.$('.t1c_in_product_class').prop('disabled', false);
                this.$('.t1c_in_product_class').prop('readonly', false);
            }

            if(current_order.is_void_order || current_order.is_return_order){
			    this.gui.show_screen('payment');
			}
		}
	});

	models.Orderline = models.Orderline.extend({
		initialize: function(attr,options){
			var self = this;
			this.line_qty_returned = 0;
			this.original_line_id = null;
			SuperOrderline.initialize.call(this,attr,options);
		},
		init_from_JSON: function (json) {
            this.line_qty_returned = json.line_qty_returned;
			this.original_line_id = json.original_line_id;
            SuperOrderline.init_from_JSON.call(this, json);
        },
		export_as_JSON: function() {
			var self = this;
			var loaded=SuperOrderline.export_as_JSON.call(this);
			loaded.line_qty_returned=self.line_qty_returned;
			loaded.original_line_id=self.original_line_id;
			return loaded;
		},
		can_be_merged_with: function(orderline){
			var self = this;
			var order = self.pos.get_order();
			if(self.pos.get_order() && (order.is_void_order || order.is_return_order) && self.quantity <0)
				return false;
			else
				return SuperOrderline.can_be_merged_with.call(this,orderline);
		}
	});

	models.Order = models.Order.extend({
		initialize: function(attributes,options){
			var self = this;
			self.approver_id = false;
            self.approve_datetime = false;
			self.return_status = '-';
			self.is_void_order = false;
			self.is_return_order = false;
			self.return_order_id = false;
			SuperOrder.prototype.initialize.call(this,attributes,options);
		},
		get_due: function(paymentline) {
			var self = this;
			if(self.is_void_order || self.is_return_order){
                var total_with_tax = Math.abs(this.get_total_with_tax());
                var total_paid = this.get_total_paid();


                if (!paymentline) {
					var due = total_with_tax - this.get_total_paid();
				}
				else {
				    var due = total_with_tax;
					var lines = this.paymentlines.models;
					for (var i = 0; i < lines.length; i++) {
						if (lines[i] === paymentline) {
							break;
						} else {
							due -= lines[i].get_amount();
						}
					}
				}
				if(Math.abs(this.change_rounding) > 0 && total_paid > 0
				&& round_pr(due, 0.01)  == round_pr(Math.abs(this.change_rounding), 0.01)){
                    due = 0;
				}

				return round_pr(Math.max(0,due), 0.01);
			}
			else{
			    return SuperOrder.prototype.get_due.call(self,paymentline);
			}
		},
		get_change: function(paymentline) {
			var self = this;
			if(self.is_void_order || self.is_return_order){

                var total_with_tax = Math.abs(this.get_total_with_tax())
                /*
                if(self.is_void_order){
                    total_with_tax -= this.change_rounding
                }
                else if(self.is_return_order){
                    total_with_tax += this.change_rounding
                }
                */
                var total_paid = this.get_total_paid();

                if (!paymentline) {
                     var change = this.get_total_paid() - total_with_tax;
                } else {
                    var change = -total_with_tax;
                    var lines  = this.paymentlines.models;
                    for (var i = 0; i < lines.length; i++) {
                        change += lines[i].get_amount();
                        if (lines[i] === paymentline) {
                            break;
                        }
                    }
                }

                if(Math.abs(this.change_rounding) > 0 && total_paid > 0 && round_pr(change, 0.01) == round_pr(Math.abs(this.change_rounding), 0.01) ){
                    change = 0;
				}

                return round_pr(Math.max(0,change), 0.01);
            }
			else{
			    return SuperOrder.prototype.get_change.call(self,paymentline);
			}
        },
		get_total_rounding: function(total){
            if(this.is_void_order){
                return SuperOrder.prototype.get_total_rounding.call(this, Math.abs(total));
            }
            else if(this.is_return_order){
                var total_integer = Math.abs(parseInt(total));
                var total_decimal = Math.abs(Math.abs(total) - Math.abs(total_integer));
                if (total_decimal > 0.75){
                    this.amount_total_rounding = total_integer + 1.00;
                }
                else if (total_decimal > 0.50 && total_decimal < 0.75){
                    this.amount_total_rounding = total_integer + 0.75;
                }
                else if (total_decimal > 0.25 && total_decimal < 0.50){
                    this.amount_total_rounding = total_integer + 0.50;
                }
                else if (total_decimal > 0.00 && total_decimal < 0.25){
                    this.amount_total_rounding = total_integer + 0.25;
                }
                else{
                    this.amount_total_rounding = Math.abs(total);
                }

                if(round_pr(this.get_total_paid(), 0.01) === round_pr(total, 0.01)){
                    this.amount_total_rounding = this.get_total_paid();
                }
                return this.amount_total_rounding;
            }
            else{
                return SuperOrder.prototype.get_total_rounding.call(this,total);
			}
        },
        get_rounding: function(){
            if(this.is_void_order || this.is_return_order){
                return this.change_rounding;
            }
            /*else if(this.is_return_order){
                var total_before = Math.abs(this.get_total_with_tax());
                var total_rounding = Math.abs(this.get_total_rounding(total_before));
                if (parseInt(this.get_total_paid()) === total_before){
                    this.change_rounding = 0.00;
                }
                else{
                    this.change_rounding = total_before - total_rounding;
                }
                return round_di(this.change_rounding, 2);
            }*/
            else{
                return SuperOrder.prototype.get_rounding.call(this);
            }
        },
        export_for_printing: function(){
            var self = this;
            var receipt = SuperOrder.prototype.export_for_printing.call(self);
            
            if(this.is_return_order){
                var new_orderlines = [];
                var promotion_discount_product_id = this.pos.config.promotion_discount_product_id[0];
                var prorate_amount = 0.0;
                var prorate_amount_exclude = 0.0;
                var prorate_vat = 0.0;

                receipt.orderlines && receipt.orderlines.forEach(function(orderline){
                    if(orderline.product_id == promotion_discount_product_id){
                        prorate_amount += Math.abs(orderline.price_with_tax);
                        prorate_amount_exclude += Math.abs(orderline.price_without_tax);
                        prorate_vat += Math.abs(orderline.tax);
                    }
                    else{
                        prorate_amount += Math.abs(orderline.prorate_amount);
                        prorate_amount_exclude += Math.abs(orderline.amount_exclude);
                        prorate_vat += Math.abs(orderline.prorate_vat);
                        new_orderlines.push(orderline);
                    }
                });
                receipt.orderlines = new_orderlines;
                receipt.total_discount = Math.abs(prorate_amount);
                receipt.discount_lines = [{
                    iface_line_tax_included: true,
                    price: -prorate_amount,
                    price_display: -prorate_amount,
                    price_with_tax: -prorate_amount,
                    price_without_tax: -prorate_amount_exclude,
                    product_id: promotion_discount_product_id,
                    product_name: "ส่วนลดสินค้าที่คืน",
                    promotion: true,
                    promotion_name: "ส่วนลดสินค้าที่คืน",
                    quantity: -1,
                    reward_type: "discount",
                    tax: prorate_vat,
                    unit_name: "Unit(s)",
                }];
            }
            return receipt
        },
		export_as_JSON: function() {
			var self = this;
			var loaded=SuperOrder.prototype.export_as_JSON.call(this);
            loaded.approver_id = this.approver_id;
            loaded.approve_datetime = this.approve_datetime;
            loaded.is_void_order = this.is_void_order;
            loaded.is_return_order = this.is_return_order;
            loaded.return_status = this.return_status;
            loaded.return_order_id = this.return_order_id;
            loaded.return_reason_id = this.return_reason_id;
            loaded.previous_invoice_id = this.previous_invoice_id;
            loaded.previous_journals = this.previous_journals;
            loaded.previous_payments = this.previous_payments;
            loaded.previous_payment_by_id = this.previous_payment_by_id;
            loaded.inv_no_old = this.inv_no_old;
			loaded.date_order_old = this.date_order_old;
			loaded.brand_id_old = this.brand_id_old;
			return loaded;
		},
		init_from_JSON: function (json) {
            this.approver_id = json.approver_id;
            this.approve_datetime = json.approve_datetime;
			this.return_status = json.return_status;
			this.is_void_order = json.is_void_order;
			this.is_return_order = json.is_return_order;
			this.return_order_id = json.return_order_id;
			this.return_reason_id = json.return_reason_id;
			this.previous_invoice_id = json.previous_invoice_id;
			this.previous_journals = json.previous_journals || {};
			this.previous_payments = json.previous_payments || [];
			this.previous_payment_by_id = json.previous_payment_by_id || {};
			this.inv_no_old = json.inv_no_old;
			this.date_order_old = json.date_order_old;
			this.brand_id_old = json.brand_id_old;
			SuperOrder.prototype.init_from_JSON.call(this, json);
        },
        reverse_promotions: function(){
            var order = this;
            if(order.is_return_order || order.is_void_order){
                return;
            }
            else{
                SuperOrder.prototype.reverse_promotions.call(this);
            }
        },
        calculate_promotion: function(coupon){
            var order = this;
            if(order.is_return_order || order.is_void_order){
                return;
            }
            else{
                return SuperOrder.prototype.calculate_promotion.call(this, coupon);
            }
        },
        apply_promotions: function(){
            var order = this;
            if(order.is_return_order || order.is_void_order){
                return {
                    diff: 0,
                    applied_promotions: [],
                };
            }
            else{
                return SuperOrder.prototype.apply_promotions.call(this);
            }
        },
        find_reward_coupons_wo_barcode: function(){
            var order = this;
            if(order.is_return_order || order.is_void_order)
                return [];
            return SuperOrder.prototype.find_reward_coupons_wo_barcode.call(this);
        }
	});

	screens.NumpadWidget.include({
		clickAppendNewChar: function(event) {
			var self = this;
			var order = self.pos.get_order();
			if(!(order.is_void_order || order.is_return_order) || (order.is_exchange_order && order.selected_orderline && !order.selected_orderline.original_line_id ))
				self._super(event);
		},
		clickSwitchSign: function() {
			var self = this;
			var order = self.pos.get_order();
			if(!(order.is_void_order || order.is_return_order) || (order.is_exchange_order && order.selected_orderline && !order.selected_orderline.original_line_id ))
				self._super();

		},
		clickDeleteLastChar: function() {
			var self = this;
			var order = self.pos.get_order();
			if(!(order.is_void_order || order.is_return_order ) || (order.is_exchange_order && order.selected_orderline && !order.selected_orderline.original_line_id ))
				self._super();	
		},
	});

	models.PosModel = models.PosModel.extend({
		set_order: function(order){
			SuperPosModel.set_order.call(this,order);
			if(order != null && !(order.is_void_order || order.is_return_order) || order.is_exchange_order ){
				$("#cancel_refund_order").hide();
			}
			else{
				$("#cancel_refund_order").show();
			}
		},
	});

	pos_orders.include({
		line_select: function(event, $line, id) {
			var self = this;
			var order = self.pos.db.order_by_id[id];
			this.$('.wk_order_list .lowlight').removeClass('lowlight');
			if ($line.hasClass('highlight')) {
				$line.removeClass('highlight');
				$line.addClass('lowlight');
				this.display_order_details('hide', order);
			} else {
				this.$('.wk_order_list .highlight').removeClass('highlight');
				$line.addClass('highlight');
				self.selected_tr_element = $line;
				var y = event.pageY - $line.parent().offset().top;
				self.display_order_details('show', order, y);
			}
		},
		display_order_details: function(visibility, order, clickpos) {
			var self = this;
			var contents = this.$('.order-details-contents');
			var parent = this.$('.wk_order_list').parent();
			var scroll = parent.scrollTop();
			var height = contents.height();
			var orderlines = [];
			var statements = [];
			var journal_ids_used = [];

			var page_type = self.get_page_type();
			if (visibility === 'show') {

				orderlines = _.values(self.pos.db.line_by_id).filter(line => (line.order_id[0] == order.id && line.line_coupon != 'reward'));

				var total_amount_return = 0.0;
				order.statement_ids.forEach(function(statement_id) {
					var statement = self.pos.db.statement_by_id[statement_id];
					if(statement){
                        statements.push(statement);
                        journal_ids_used.push(statement.journal_id[0]);
					    if(statement.line_amount_returned)
					        total_amount_return += statement.line_amount_returned;
					}
				});
				contents.empty();
				var page_type_str = (page_type=='void')?'Void':(page_type=='return')?'Return':'';
				contents.append($(QWeb.render('OrderDetails', {
				    widget: this,
				    order: order,
				    orderlines: orderlines,
				    statements: statements,
				    page_type: page_type_str,
				    total_amount_return: total_amount_return,
                })));
				var new_height = contents.height();
				if (!this.details_visible) {
					if (clickpos < scroll + new_height + 20) {
						parent.scrollTop(clickpos - 20);
					} else {
						parent.scrollTop(parent.scrollTop() + new_height);
					}
				} else {
					parent.scrollTop(parent.scrollTop() - height + new_height);
				}
				this.details_visible = true;

				var close_order_details_$el = self.$el.find("#close_order_details");
				close_order_details_$el.off("click");
				close_order_details_$el.on("click", function() {
					self.selected_tr_element.removeClass('highlight');
					self.selected_tr_element.addClass('lowlight');
					self.details_visible = false;
					self.display_order_details('hide', null);
				});

				var wk_refund_$el = self.$el.find("#wk_refund");
				wk_refund_$el.off("click");
				wk_refund_$el.on("click", function(){
                    self.click_void_return(self, order)
                });
			}
			if (visibility === 'hide') {
				contents.empty();
				if (height > scroll) {
					contents.css({ height: height + 'px' });
					contents.animate({ height: 0 }, 400, function() {
						contents.css({ height: '' });
					});
				} else {
					parent.scrollTop(parent.scrollTop() - height);
				}
				this.details_visible = false;
			}
		},
		click_void_return: function(self, order){
			var page_type = self.get_page_type();
		    var order_list = self.pos.db.pos_all_orders;
            var order_line_data = self.pos.db.pos_all_order_lines;
            var message = '';
            var non_returnable_products = false;
            var original_orderlines = [];
            var include_promotion = false;
            var allow_return = true;

            var empty_orderline = true;
            order.lines.forEach(function(line_id){
                var line = self.pos.db.line_by_id[line_id];
                if(line.line_qty_returned && Math.abs(line.qty) - Math.abs(line.line_qty_returned) > 0){
                    empty_orderline = false;
                }
                else if(line.line_qty_returned === undefined || line.line_qty_returned == 0){
                    empty_orderline = false;
                }
            });
            if(order.return_status == 'Fully-Returned' || empty_orderline){
                message = 'No items are left to return for this order!!'
                allow_return = false;
            }
            var all_pos_orders = self.pos.get('orders').models || [];
            var return_order_exist = _.find(all_pos_orders, function(pos_order){
                if(pos_order.return_order_id && pos_order.return_order_id == order.id)
                    return pos_order;
            });

            var free_line_ids = [];
            var coupon_line_ids = [];
            if(return_order_exist){
                self.gui.show_popup('my_message',{
                    'title': _t('Refund Already In Progress'),
                    'body': _t("Refund order is already in progress. Please proceess with Order Reference " + return_order_exist.sequence_number),
                });
            }
            else if (allow_return) {
                var original_orderlines_dict = _.values(self.pos.db.line_by_id).filter(line => (line.order_id[0] == order.id))

                original_orderlines_dict.forEach(function(line){
                    include_promotion |= line.promotion;
                });

                if(page_type == 'void'){
                    //prepare for fully return
                    original_orderlines = original_orderlines_dict;
                }
                else if(page_type == 'return'){
                    //case return
                    var discount_product_id = self.pos.config.promotion_discount_product_id[0];
                    var free_lines = [];
                    original_orderlines_dict.forEach(function(line){
                        //only remaining qty
                        if(discount_product_id == line.product_id[0]){
                            if(line.free_product_id){
                                // free product line qty is less than zero
                                free_lines.push(_.recursiveDeepCopy(line));
                            }
                            // otherwise is discount line no need for return
                        }
                        else if(line.qty - line.line_qty_returned > 0)
                            original_orderlines.push(_.recursiveDeepCopy(line));
                        else if(line.line_coupon == 'reward_coupon'){
                            var coupon = _.recursiveDeepCopy(line)
                            coupon.qty = Math.abs(coupon.qty);
                            original_orderlines.push(coupon);
                        }
                    });

                    //add the information on original free product line (positive side)
                    free_lines.forEach(function(free_line){
                        original_orderlines.forEach(function(line){
                            if(line.promotion && line.promotion_id[0] == free_line.promotion_id[0]
                            && line.promotion_condition_id[0] == free_line.promotion_condition_id[0]
                            && line.product_id[0] == free_line.free_product_id[0]){
                                line.promotion_name = free_line.promotion_name;
                                line.promotion_id = free_line.promotion_id;
                                line.free_product_id = free_line.free_product_id;
                                line.line_free_id = free_line.id;

                                // for tracking back
                                free_line_ids.push(line.id);
                            }
                        });
                    });
                    original_orderlines = original_orderlines.filter((line)=> line.qty - line.line_qty_returned > 0);
                }
                else{
                    order.lines.forEach(function(line_id){
                        var line = self.pos.db.line_by_id[line_id];
                        var product = self.pos.db.get_product_by_id(line.product_id[0]);
                        if(product == null){
                            non_returnable_products = true;
                            message = 'Some product(s) of this order are unavailable in Point Of Sale, do you wish to return other products?'
                        }
                        else if (product.not_returnable) {
                            non_returnable_products = true;
                            message = 'This order contains some Non-Returnable products, do you wish to return other products?'
                        }
                        else if(line.qty - line.line_qty_returned > 0)
                            original_orderlines.push(line);
                    });
                }

                if(original_orderlines.length == 0){
                    self.gui.show_popup('my_message',{
                        'title': _t('Cannot Return This Order!!!'),
                        'body': _t("There are no returnable products left for this order. Maybe the products are Non-Returnable or unavailable in Point Of Sale!!"),
                    });
                }
                else if(non_returnable_products){
                    self.gui.show_popup('confirm',{
                        'title': _t('Warning !!!'),
                        'body': _t(message),
                        confirm: function(){
                            self.gui.show_popup('return_products_popup',{
                                'order':order,
                                'orderlines': original_orderlines,
                                'is_partial_return':true,
                                'page_type': page_type,
                                'approver': self.get_approver(),
                                'free_line_ids': free_line_ids,
                                'include_promotion': include_promotion,
                            });
                        },
                    });
                }
                else{
                    self.gui.show_popup('return_products_popup',{
                        'order':order,
                        'orderlines': original_orderlines,
                        'is_partial_return':false,
                        'page_type': page_type,
                        'approver': self.get_approver(),
                        'free_line_ids': free_line_ids,
                        'include_promotion': include_promotion,
                    });
                }
            }
            else{
                self.gui.show_popup('my_message',{
                    'title': _t('Warning!!!'),
                    'body': _t(message),
                });
            }
		},
		show: function(){
			var self = this;
			this._super();
			var self = this;
			this.details_visible = false;
			this.selected_tr_element = null;
			self.$('.wk-order-list-contents').delegate('.wk-order-line', 'click', function(event) {
				self.line_select(event, $(this), parseInt($(this).data('id')));
			});
			var contents = this.$('.order-details-contents');
			contents.empty();
			var parent = self.$('.wk_order_list').parent();
			parent.scrollTop(0);
		},
	});

	return {
	    OrderReturnPopup: OrderReturnPopup,
	};
});