/* Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>) */
/* See LICENSE file for full copyright and licensing details. */
/* License URL : <https://store.webkul.com/license.html/> */
odoo.define('pos_orders.pos_orders',function(require){
	"use strict"
	var PosDB = require('point_of_sale.DB');
	var Model = require('web.DataModel');
	var screens = require('point_of_sale.screens');
	var gui = require('point_of_sale.gui');
	var models = require('point_of_sale.models');
	var utils = require('web.utils');
	var core = require('web.core');
	var QWeb = core.qweb;
	var SuperPosModel = models.PosModel.prototype;
    var _t = core._t;


    var session = require('web.session');

    models.load_models([{
        model:  'ir.config_parameter',
        fields: ['key','value'],
        domain: function(self){ return [ ['key','in', ['pos_order_void','pos_order_return']] ]; },
        limit: 2,
        loaded: function(self, parameters){
            parameters.forEach(function(parameter){
                if(parameter.key == 'pos_order_void'){
                    self.system_parameter_pos_order_void = (parameter.value == 'True')?true: false;
                }
                else if(parameter.key == 'pos_order_return'){
                    self.system_parameter_pos_order_return = (parameter.value == 'True')?true: false;
                }
            });
        },
    }]);

	models.load_models([{
			label: 'pos.order',
			loaded: function(self) {
				self.db.order_by_id = {};
			},
		}, {
			label: 'pos.order.line',
			loaded: function(self) {
				self.db.line_by_id = {};
			},
		}, {
			label: 'account.bank.statement.line',
			loaded: function(self) {
				self.db.statement_by_id = {};
			},
		}], {
		'after': 'product.product'
	});

	models.PosModel = models.PosModel.extend({
		get_user_by_userid: function(id){
		    var users = this.users;
		    for(var i = 0 ; i <users.length ; i++){
		        if(users[i].id == id){
		            return users[i];
		        }
		    }
		    return false;
		},
		/*
		_save_to_server: function (orders, options) {
			var self = this;
			return SuperPosModel._save_to_server.call(this,orders,options).then(function(return_dict){
				return return_dict.order_ids;
            });
		},
		*/
	});

	PosDB.include({
	    pos_order_fields: function(){
            return this._super().concat(['return_order_id', 'is_void_order', 'is_return_order', 'return_status']);
        },
        pos_order_line_fields: function(){
            return this._super().concat(['line_qty_returned']);;
        },
    });

	var OrdersScreenWidget = screens.ScreenWidget.extend({
		template: 'OrdersScreenWidget',
		order_domain: function(self, inv_no, page_type) {
			page_type = page_type || self.get_page_type();
            var domain_list = [['branch_id', '=', self.pos.config.branch_id[0]], ['inv_no', '=', inv_no]];
            if (page_type == 'void') {
                if(self.pos.config.order_loading_options == 'n_days'){
                    var today = new Date();
                    var validation_date = new Date(today.setDate(today.getDate()-self.pos.config.number_of_days)).toISOString();
                    domain_list.push(['date_order','>',validation_date]);
                }
                else if (self.pos.config.order_loading_options == 'current_session') {
                    domain_list.push(['session_id', '=', self.pos.pos_session.name]);
                }
                domain_list.push(['invoice_id', '=', false]);
            }
            else if(page_type == 'return'){
                if(self.pos.config.return_order_loading_options == 'n_days'){
                    var today = new Date();
                    var validation_date = new Date(today.setDate(today.getDate()-self.pos.config.return_number_of_days)).toISOString();
                    domain_list.push(['date_order','>',validation_date]);
                }
                else if (self.pos.config.return_order_loading_options == 'current_session') {
                    domain_list.push(['session_id', '=', self.pos.pos_session.name]);
                }
            }
            domain_list.push(['state', 'not in', ['draft', 'cancel']]);
            domain_list.push(['is_void_order', '=', false]);
            domain_list.push(['is_return_order', '=', false]);
            domain_list.push(['return_status', '!=', 'Fully-Returned']);
            return domain_list;
        },
        order_lines_domain: function(self, orders) {
            var order_ids = []
            if(!(orders instanceof Array)){
                orders = [orders];
            }
            for (var i = 0; i < orders.length; i++) {
                order_ids.push(orders[i]['id']);
            }
            return [
                ['order_id', 'in', order_ids]
            ];
        },
        statement_ids_domain: function(self, orders) {
            var statement_ids = []
            if(!(orders instanceof Array)){
                orders = [orders];
            }
            for (var i = 0; i < orders.length; i++) {
                statement_ids = statement_ids.concat(orders[i]['statement_ids']);
            }
            return [
                ['id', 'in', statement_ids]
            ];
        },
        search_read_api: function(model, domain, limit){
            if(model === undefined){
                console.error('search read api model not found');
                return false;
            }
            else{
                return session.rpc('/web/dataset/search_read', {
                    model: model.model,
                    fields: model.fields || [],
                    domain: domain || [],
                    context: model.context,
                    limit: limit || false,
                }).then(function(result){
                    return result.records;
                });
            }
        },
		order_request: async function(inv_no, page_type){
		    var self = this;
			page_type = page_type || self.get_page_type();
		    self.chrome.loading_show();
            self.chrome.loading_message(_t('Looking for the Order ') + inv_no, 0.1);
            var orders = await self.search_read_api({
                        model: 'pos.order',
                        fields: self.pos.db.pos_order_fields(),
                    },
                    self.order_domain(self, inv_no, page_type),
                    1,
            );

            if(page_type == 'return'){
                orders = orders.filter(function(order){
                    if(order.session_id[0] != self.pos.pos_session.id)
                        return true;
                    else if(order.session_id[0] == self.pos.pos_session.id && order.invoice_id)
                        return true;
                    else
                        return false;
                });
            }
            if (!orders|| orders.length == 0){
                return false;
            }

            orders && orders.forEach(function(order){
                self.pos.db.order_by_id[order.id] = order;
            });
            self.chrome.loading_progress(0.4);

            var lines = await self.search_read_api({
                    model:'pos.order.line',
                    fields: self.pos.db.pos_order_line_fields(),
                },
                self.order_lines_domain(self, orders),
            );
            if(!lines || lines.length == 0){
                return false;
            }
            var no_product_ids = [];
            var no_promotion_ids = [];
            var no_condition_ids = [];
            var no_condition_mapping_ids = [];
            lines && lines.forEach(function(line){
                self.pos.db.line_by_id[line.id] = line;
                if(!(line.product_id[0] in self.pos.db.product_by_id) && !no_product_ids.includes(line.product_id[0])){
                    no_product_ids.push(line.product_id[0]);
                }
                if(line.promotion_id && !(line.promotion_id[0] in self.pos.db.promotion_by_id)
                && !no_promotion_ids.includes(line.promotion_id[0])){
                    no_promotion_ids.push(line.promotion_id[0]);
                }
                if(line.promotion_condition_id && !(line.promotion_condition_id[0] in self.pos.db.promotion_condition_by_id)
                && !no_condition_ids.includes(line.promotion_condition_id[0])){
                    no_condition_ids.push(line.promotion_condition_id[0]);
                }
            });
            self.chrome.loading_progress(0.5);

            if(no_promotion_ids.length > 0){
                self.chrome.loading_progress(0.6);
                var promotions = await self.search_read_api(
                    self.pos.find_model('pos.promotion'),
                    [['id', 'in', no_promotion_ids]],
                );
                if(promotions){
                    self.pos.db.add_promotions(promotions);
                }
            }

            if(no_condition_ids.length > 0){
                self.chrome.loading_progress(0.7);
                var promotion_conditions = await self.search_read_api(
                    self.pos.find_model('pos.promotion.condition'),
                    [['id', 'in', no_condition_ids]],
                );
                if(promotion_conditions){
                    self.pos.db.add_promotion_conditions(promotion_conditions);
                    promotion_conditions.forEach(function(condition){
                        condition.condition_apply_id = 0;
                        if(condition.promotion_condition_product_qty_ids && condition.promotion_condition_product_qty_ids.length > 0){
                            no_condition_mapping_ids = no_condition_mapping_ids.concat(condition.promotion_condition_product_qty_ids);
                        }
                    });
                }
            }

            if(no_condition_ids.length > 0){
                self.chrome.loading_progress(0.75);
                var condition_product_qty = await self.search_read_api(
                    self.pos.find_model('promotion.mapping.product.qty'),
                    [['promotion_condition_id', 'in', no_condition_ids]],
                );
                if(condition_product_qty){
                    self.pos.db.add_promotion_condition_product_qty(condition_product_qty);
                }
            }


            var statements = await self.search_read_api({
                    model:'account.bank.statement.line',
                    fields: [
                        'id','journal_id','amount', 'credit_card_no',
                        'credit_card_type', 'credit_card_no_encrypt',
                        'approve_code', 'line_amount_returned', 't1cc_barcode', 
                        't1cp_receipt_no','transactions','api_to_be_cancelled', 
                        'api_cancel_success'
                    ],
                },
                self.statement_ids_domain(self, orders),
            );

            if(!statements || statements.length == 0){
                return false;
            }

            var new_statements = [];
            //sum cash between paid cash and change change to be actual cash
            var cash_statement = undefined;
            statements && statements.forEach(function(statement){
                var cashregister = null;
                for ( var i = 0; i < self.pos.cashregisters.length; i++ ) {
                    if ( self.pos.cashregisters[i].journal_id[0] === statement.journal_id[0] ){
                        cashregister = self.pos.cashregisters[i];
                        break;
                    }
                }

                if(cashregister && cashregister.journal.type == 'cash' && (!cashregister.journal.redeem_type_id || page_type == 'return')){//return and void case for t1c
                    //merge cash
                    if(cash_statement){
                        cash_statement.amount += statement.amount;
                        cash_statement.line_amount_returned += statement.line_amount_returned;
                        cash_statement.id = statement.id;
                    }
                    else{
                        cash_statement = statement;
                        new_statements.push(statement);
                    }
                }
                else{
                    new_statements.push(statement);
                }
            });

            statements = new_statements;
            if(!statements || statements.length == 0){
                return false;
            }
            statements && statements.forEach(function(statement){
                self.pos.db.statement_by_id[statement.id] = statement;
            });
            self.chrome.loading_progress(0.8);

            if(no_product_ids.length > 0){
                var products = await self.search_read_api(
                    self.pos.find_model('product.product'),
                    [ ['id', 'in', no_product_ids] ],
                );

                if(products && products.length){
                    self.pos.db.add_products(products);
                }
            }
            return {
                orders: orders,
                lines: lines,
                statements: statements,
            }


		},
		get_customer: function(customer_id){
			var self = this;
			if(self.gui)
				return self.gui.get_current_screen_param('customer_id');
			else
				return undefined;
		},
		get_page_type: function(){
			var self = this;
			if(self.gui)
				return self.gui.get_current_screen_param('page_type');
			else
				return undefined;
		},
		get_approver: function(){
			var self = this;
			if(self.gui)
				return self.gui.get_current_screen_param('approver');
			else
				return undefined;
		},
		render_list: function(order, input_txt) {
			var self = this;
			var customer_id = this.get_customer();
			var new_order_data = [];
			if(customer_id != undefined){
				for(var i=0; i<order.length; i++){
					if(order[i].partner_id[0] == customer_id)
						new_order_data = new_order_data.concat(order[i]);
				}
				order = new_order_data;
			}
			if (input_txt != undefined && input_txt != '') {
				var new_order_data = [];
				var search_text = input_txt.toLowerCase()
				for (var i = 0; i < order.length; i++) {
					if (order[i].partner_id == '') {
						order[i].partner_id = [0, '-'];
					}
					if (((order[i].inv_no.toLowerCase()).indexOf(search_text) != -1)
					    || ((order[i].name.toLowerCase()).indexOf(search_text) != -1)
					    || ((order[i].partner_id[1].toLowerCase()).indexOf(search_text) != -1)) {
						new_order_data = new_order_data.concat(order[i]);
					}
				}
				order = new_order_data;
			}
			var contents = this.$el[0].querySelector('.wk-order-list-contents');
			contents.innerHTML = "";
			var wk_orders = order;
			for (var i = 0, len = Math.min(wk_orders.length, 1000); i < len; i++) {
				var wk_order = wk_orders[i];
				var orderline_html = QWeb.render('WkOrderLine', {
					widget: this,
					order: wk_orders[i],
					customer_id:wk_orders[i].partner_id[0],
				});
				var orderline = document.createElement('tbody');
				orderline.innerHTML = orderline_html;
				orderline = orderline.childNodes[1];
				contents.appendChild(orderline);
			}
		},
		show: function() {
			var self = this;
			this._super();
			//note: pos_all_orders not same length as order_by_id when there retrieve of return
			var page_type = this.get_page_type();

			if(page_type == 'void'){
			    this.$el.find('.void_return_type').html('Void');
            }
			else if(page_type == 'return'){
			    this.$el.find('.void_return_type').html('Return');
			}
            this.render_list([] , undefined);

			this.$('.order_search').val('');
			this.$('.order_search').focus();
			this.$('.order_search').off('blur');
			this.$('.order_search').off('keypress');
			this.$('.order_search').keypress(function(event) {
                if(event.target && event.target.tagName.toUpperCase() == 'INPUT') {
                    if(event.keyCode == 13) {
                        event.preventDefault();
                        return $(event.target).blur();
                    }
                }
			});
			this.$('.order_search').off('blur');
			this.$('.order_search').on('blur', function() {
			    this.value = this.value.trim();
			    var inv_no_value = this.value;
                if(this.value.length != 0){
                    self.order_request(inv_no_value, page_type).then(function(result){
                        self.chrome.loading_hide();
                        if(result.orders){
                            self.render_list(result.orders, undefined);
                            var orderlist = self.$('.wk-order-line');
                            if(orderlist.length > 0){
                                orderlist[0].click();
                            }
                            return;
                        }
                        else{
                            var orderlist = self.$('.wk-order-line');
                            if(orderlist.length > 0){
                                orderlist[0].click();
                            }
                            self.render_list([], undefined);
                            self.gui.show_popup('alert', {
                                'title': _t('Order Not Found'),
                                'body': _t('Receipt ') +
                                        inv_no_value+
                                        _t(' not found '),
                            });
                            return;
                        }
                    }, function(err){
                        self.chrome.loading_hide();
                        console.error(err);
                    });
                }
			});
			this.$('.back').on('click',function() {
				self.gui.show_screen('products');
			});
		},
		close: function() {
			this._super();
			this.$('.wk-order-list-contents').undelegate();
		},
	});
	gui.define_screen({name: 'wk_order',widget:OrdersScreenWidget});

	screens.ProductScreenWidget.include({
		show: function(){
			var self = this;
			this._super();
			this.product_categories_widget.reset_category();
			this.numpad.state.reset();
			$('.all_orders').on('click',function(){
                var current_order = self.pos.get_order();
                var page_type = $(this).hasClass('return-condition')?'return':'void';
                if(current_order.get_orderlines().length > 0){
				    self.gui.show_popup('alert', {
                        'title': 'Alert',
                        'body': 'ไม่สามารถทำรายการได้ กรุณาลบรายการสินค้าที่หน้าหลัก'
                    });
				    return;
				}
				self.ask_manager_ask_pin().then(function(approver){
                    self.gui.show_screen('wk_order', {
                        'customer_id':this.id,
                        'page_type': page_type,
                        'approver': approver,
                    });
				});
			});
		},
	});

	screens.ClientListScreenWidget.include({
		show: function() {
			var self = this;
			self._super();
			$('.view_all_order').on('click',function() {
			    var customer_id = this.id;
				self.ask_manager_ask_pin().then(function(approver){
                    self.gui.show_screen('wk_order', {
                        'customer_id': customer_id,
                        'page_type': 'void',
                        'approver': approver,
                    });
				});
			});
		}
	});

	return OrdersScreenWidget;
});
