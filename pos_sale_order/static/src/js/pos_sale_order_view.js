odoo.define('pos_sale_order.view', function (require) {
    "use strict";
    var PosBaseWidget = require('point_of_sale.BaseWidget');
    var core = require('web.core');
    var models = require('point_of_sale.models');
    var Model = require('web.DataModel');
    var gui = require('point_of_sale.gui');
    var PosDB = require('point_of_sale.DB');
    var session = require('web.session');
	var screens = require('point_of_sale.screens');
	var utils = require('web.utils');
	var QWeb = core.qweb;
	var web_client = require('web.web_client');
	var ofm_the_one_card = require('ofm_the_one_card.the_one_card');
    var pos_orders = require('pos_orders.pos_orders');
    var pos_order_return_popup = require('pos_order_return.pos_order_return');
    var CardListScreenWidget = ofm_the_one_card.CardListScreenWidget;

    var _t = core._t;


    var action_button_classes = [];

    var SaleOrderReturnPopup = pos_order_return_popup.OrderReturnPopup.extend({
        template: 'SaleOrderReturnPopup',
		request_refund_invoice_new_tab: function(id){
            if(id){
                var url = '/web#id=' + id + '&';
                url += this.pos.menu_account_refund;
                window.open(url ,'_blank');
            }
        },
        request_menu_customer_payments: function(id){
            if(id){
                var url = '/web#id=' + id + '&';
                url += this.pos.menu_customer_payments;
                window.open(url ,'_blank');
            }
        },
		call_api_return_sale_order: function(json_pass){
		    var self = this;
		    // close the popup
            self.click_cancel();
		    self.chrome.loading_show();
            self.chrome.loading_message(_t('On process Return ') + json_pass.title, 0.75);

		    return new Model('sale.order').call('return_so_from_ui',
                [json_pass.sale_order_return]
            ).then(function(result){
                if(result.account_invoice_id)
                    self.request_refund_invoice_new_tab(result.account_invoice_id);
                if(result.account_payment_id)
                    self.request_menu_customer_payments(result.account_payment_id);
                self.gui.show_screen('sale_order_list');
                self.chrome.loading_hide();
		    }, function(err){
		        console.error(err)
		        self.chrome.loading_hide();
		    })
		},
		create_return_order: function(return_dict, return_reason_id){
			var self = this;
			var order = self.options.order;

            var order_id = order.id;

            return_dict = return_dict.filter((line)=> line.qty != 0);

            var json_pass = {
                "title": order.name,
                "sale_order_return": {
                    "order_id": order_id,
                    "return_reason_id": parseInt(return_reason_id),
                    "return_approver_id": self.options.approver.id,
                    "return_approve_datetime": self.options.approver.datetime,
                    "order_lines": return_dict,
                }
            };

            self.call_api_return_sale_order(json_pass);
		},
		click_return_order: function(event, force_validation = false){
			var self = this;
			var all = $('.return_qty');
			var return_dict = [];
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
                    return_dict.push({
                        id : line_id,
                        qty: qty_input,
                    });
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
                        return_dict.push({
                            id : line_free_id,
                            qty: (-1)*qty_input,
                        });
                    }
				}
				if(qty_input != 0)
				    all_zero = false;
			});
			var return_reason_box = $('.return_so_reason_selection_box');
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

            var total_previous_cash = 0.0;
            var cash_found = false;
            if(return_entries_ok && self.options.is_partial_return){
                var total_amount_return = 0.0;
                return_dict.forEach(function(line){
                    var line = self.pos.db.line_by_id[line.id];
                    total_amount_return += line.price_unit * parseFloat(line.qty)
                });
            }
            
            /*if(!force_validation && self.options.page_type == 'return'
            && return_entries_ok && !self.check_return_promotion(self, remaining_line)){
                return_entries_ok = false;
            }*/
			if(return_entries_ok){
                if(return_dict.length > 0){
				    var refund_order = self.create_return_order(return_dict, return_reason_id);
                }
            }
		},
    });
    gui.define_popup({ name: 'so_return_products_popup', widget: SaleOrderReturnPopup });

    var SaleOrderReturnScreenWidget = pos_orders.extend({
        template: 'SaleOrderReturnScreenWidget',
		state_dict: {
            'draft': 'Quotation',
            'sent': 'SO Draft',
            'sale': 'Sales Order',
            'done': 'Locked',
            'cancel': 'Cancelled',
		},
		click_void_return: function(self, order){
            /*
                for displaying the return popup
            */
			var page_type = 'return';
		    var order_list = self.pos.db.pos_all_orders;
            var order_line_data = self.pos.db.pos_all_order_lines;
            var message = '';
            var original_orderlines = [];
            var allow_return = true;
            var empty_orderline = true;
            order.lines.forEach(function(line){
                if(line.line_qty_returned && Math.abs(line.product_uom_qty) - Math.abs(line.line_qty_returned) > 0){
                    empty_orderline = false;
                }
                else if(line.line_qty_returned === undefined || line.line_qty_returned == 0){
                    empty_orderline = false;
                }
            });

            var free_line_ids = [];
            if(order.return_status == 'Fully-Returned' || empty_orderline){
                message = 'No items are left to return for this order!!'
                allow_return = false;
            }
            else if (allow_return) {
                var original_orderlines_dict = _.values(self.pos.db.line_by_id).filter(line => (line.order_id[0] == order.id))

                if(page_type == 'return'){
                    //case return
                    var discount_product_id = self.pos.config.promotion_discount_product_id[0];
                    // console.log(discount_product_id)
                    var free_lines = [];
                    // console.log(original_orderlines_dict);
                    original_orderlines_dict.forEach(function(line){
                        //only remaining qty
                        if(line.is_type_delivery_by_order)
                            return;
                        if(discount_product_id == line.product_id[0]){
                            if(line.free_product_id){
                                // free product line qty is less than zero
                                free_lines.push(_.recursiveDeepCopy(line));
                            }
                            // otherwise is discount line no need for return
                        }
                        else if(line.product_uom_qty - line.line_qty_returned > 0)
                            original_orderlines.push(_.recursiveDeepCopy(line));
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
                    original_orderlines = original_orderlines.filter((line)=> line.product_uom_qty - line.line_qty_returned > 0);
                }

                if(original_orderlines.length == 0){
                    self.gui.show_popup('my_message',{
                        'title': _t('Cannot Return This Order!!!'),
                        'body': _t("There are no returnable products left for this order. Maybe the products are Non-Returnable or unavailable in Point Of Sale!!"),
                    });
                }
                else{
                    self.gui.show_popup('so_return_products_popup',{
                        'order':order,
                        'orderlines': original_orderlines,
                        'is_partial_return':false,
                        'page_type': page_type,
                        'approver': self.get_approver(),
                        'free_line_ids': free_line_ids,
                        // 'include_promotion': true,
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
        display_order_details: function(visibility, order, clickpos) {
            var self = this;
            var contents = this.$el.find('.order-details-contents');
            var parent = this.$el.find('.wk_order_list').parent();
            var scroll = parent.scrollTop();
            var height = contents.height();
            var orderlines = [];
            var statements = [];
            var journal_ids_used = [];

            if (visibility === 'show') {
                orderlines = _.values(self.pos.db.line_by_id).filter(line => (line.order_id[0] == order.id));
                contents.empty();
                var page_type_str = 'Return';
                contents.append($(QWeb.render('SaleOrderReturnDetails', {
                    widget: this,
                    order: order,
                    orderlines: orderlines,
                    page_type: page_type_str,
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

                var wk_refund_$el = self.$el.find("#wk_refund")
                wk_refund_$el.off("click")
                wk_refund_$el.on("click", function(){
                    Object.assign(order, {lines: orderlines}); //appending orderlines to order, preparing for void_return
                    self.click_void_return(self, order);
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
        order_lines_domain: function(self, orders) {
            /* 
                returns domain for order_lines
            */
            var order_ids = []
            if(!(orders instanceof Array)){
                orders = [orders];
            }
            for (var i = 0; i < orders.length; i++) {
                order_ids.push(orders[i]['id']);
            }
            var domain = [['order_id', 'in', order_ids],]
            return domain;
        },
        order_request: async function(so_no){
            /*
                requests orders and order lines from sale_order where state is in sale or done
            */
            var self = this;
            self.chrome.loading_show();
            self.chrome.loading_message(_t('Looking for the Order ') + so_no, 0.1);
            var orders = await session.rpc('/web/search_sale_order_api/', {
                    key: so_no,
                    sale_type: (odoo.session_info.sale_type == 'dropship')
                }).then(function(result){
                    return result.records;
                });

            orders && orders.forEach(function(order){
                self.pos.db.order_by_id[order.id] = order;
            });
            self.chrome.loading_progress(0.4);

            var lines = await self.search_read_api({
                    model:'sale.order.line',
                    fields: [],
                },
                self.order_lines_domain(self, orders),
            );
            if(!lines || lines.length == 0){
                return false;
            }

            var no_product_ids = [];
            lines && lines.forEach(function(line){
                self.pos.db.line_by_id[line.id] = line;
                if(!(line.product_id[0] in self.pos.db.product_by_id)){
                    no_product_ids = _.union([line.product_id[0]], no_product_ids);
                }
            });

            var has_product_db = [];
            if(self.pos.db.products && self.pos.db.products.length)
                has_product_db = self.pos.db.products.filter((product)=> no_product_ids.includes(product.id));
            var has_product_ids = [];
            if(has_product_db.length){
                has_product_db.forEach(function(product){
                    self.pos.db.product_by_id[product.id] = product;
                    has_product_ids.push(product.id)
                });
            }
            no_product_ids = _.difference(has_product_ids, no_product_ids);

            if(no_product_ids.length > 0){
                var products = await self.search_read_api(
                    self.pos.find_model('product.product'),
                    [ ['id', 'in', no_product_ids] ],
                );

                if(products && products.length){
                    products.forEach(function(product){
                        self.pos.db.product_by_id[product.id] = product;
                    });
                }
            }

            self.chrome.loading_progress(0.8);

            return {
                orders: orders,
                lines: lines,
            }
        },

        render_list: function(order, input_txt) {
            /*
                outputs expanding Qweb view of order
            */
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
            var contents = this.$el[0].querySelector('.return-wk-order-list-contents');
            contents.innerHTML = "";
            var wk_orders = order;
            for (var i = 0, len = Math.min(wk_orders.length, 1000); i < len; i++) {
                var wk_order = wk_orders[i];
                var orderline_html = QWeb.render('SaleOrderReturnLines', {
                    widget: this,
                    order: wk_orders[i],
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
            var back_$el = this.$el.find('.back');
            back_$el.off('click');
            back_$el.on('click',function() {
                self.gui.show_screen('sale_order_list');
            });

            var order_search_$el =  this.$el.find('.order_search');
            order_search_$el.val('');
            order_search_$el.focus();
            order_search_$el.off('blur');
            order_search_$el.off('keypress');
            order_search_$el.off('change');
            order_search_$el.on('keypress', this.enter_to_blur);
            order_search_$el.on('blur', function() {
                this.value = this.value.trim();
                var so_no = this.value;
                if (this.value.length != 0){
                    self.order_request(so_no).then(function(result){
                        // console.log(result.orders);
                        self.chrome.loading_hide();
                        if (result.orders){
                            self.render_list(result.orders, undefined);
                            var orderlist = self.$el.find('.return-wk-order-line');
                            if (orderlist.length == 1){
                                orderlist[0].click();
                            }
                            return;
                        }
                        else{
                            self.render_list([], undefined);
                            self.gui.show_popup('alert', {
                                'title': _t('Order Not Found'),
                                'body': so_no +
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

            this.$el.find('.return-wk-order-list-contents').off('click', '.return-wk-order-line');
            this.$el.find('.return-wk-order-list-contents').on('click', '.return-wk-order-line', function(event) {
                self.line_select(event, $(this), parseInt($(this).data('id')));
            });
        },
    });
    gui.define_screen({name:'sale_order_return_form', widget: SaleOrderReturnScreenWidget});

    /* -------- The Sale Order List Screen -------- */
    var SaleOrderListScreenWidget = screens.ScreenWidget.extend({
		template: 'SaleOrderListScreenWidget',
		state_dict: {
            'draft': 'Quotation',
            'sent': 'SO Draft',
            'sale': 'Sales Order',
            'done': 'Locked',
            'cancel': 'Cancelled',
		},
		search_state: ['draft', 'sent'],
		order_domain: function(self, inv_no) {
			page_type = page_type || self.get_page_type();
            var domain_list = [
                '|'
                ['branch_id', '=', self.pos.config.branch_id[0]],
                ['quotation_no', '=', inv_no]
            ];
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
		order_request: async function(so_no){
		    var self = this;
		    self.chrome.loading_show();
            self.chrome.loading_message(_t('Looking for the Order ') + so_no, 0.1);
            var orders = await session.rpc('/web/search_sale_order_api/', {
                    key: so_no,
                    sale_type: (odoo.session_info.sale_type == 'dropship')
                }).then(function(result){
                    return result.records;
                });

            if(orders){
                orders = orders.filter(order=> self.search_state.includes(order.state));

                orders.forEach(function(order){
                    self.pos.db.order_by_id[order.id] = order;
                });
            }

            if(!orders || orders.length == 0){
                return false;
            }

            self.chrome.loading_progress(0.4);

            var lines = await self.search_read_api({
                    model:'sale.order.line',
                    fields: [],
                },
                self.order_lines_domain(self, orders),
            );
            if(!lines || lines.length == 0){
                return false;
            }

            self.chrome.loading_progress(0.8);

            return {
                orders: orders,
                lines: lines,
            }
		},
		get_customer: function(customer_id){
			var self = this;
			if(self.gui)
				return self.gui.get_current_screen_param('customer_id');
			else
				return undefined;
		},
        render_list: function(order, input_txt) {
			var self = this;
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
			var contents = this.$el[0].querySelector('.sale-order-list-contents');
			contents.innerHTML = "";
			var wk_orders = order;
			for (var i = 0, len = Math.min(wk_orders.length, 1000); i < len; i++) {
				var wk_order = wk_orders[i];
				var orderline_html = QWeb.render('SaleOrderListLine', {
					widget: this,
					order: wk_orders[i],
					//customer_id:wk_orders[i].partner_id[0],
				});
				var orderline = document.createElement('tbody');
				orderline.innerHTML = orderline_html;
				orderline = orderline.childNodes[1];
				contents.appendChild(orderline);
			}
		},
		line_select: async function(event, $line, id) {
			var self = this;

            self.chrome.loading_show();
            self.chrome.loading_message('กรุณารอสักครู่ ระบบกำลังดึงข้อมูล', 0.5);
			var orders = await session.rpc('/web/search_sale_order_api/', {
                    object_id: id,
                }).then(function(result){
                    return result.records;
                }).always(function(){
                    self.chrome.loading_hide();
                });

            var found = false;
            orders.forEach(function(order){
                if(order.id == id)
                    found = true;
                self.pos.db.order_by_id[order.id] = order;
            });
            var order = self.pos.db.order_by_id[id];
            if(found && order.order_line){
                //console.log(order);
                self.pos.set_sale_order_from_db(order.id);
                //console.log('order_obj', order_obj);
                self.gui.show_screen('sale_order_form');
            }
		},
        show: function() {
            var self = this;
            this._super();
            var next_$el = this.$el.find('.next');
            next_$el.off('click');
            next_$el.on('click',function() {
				self.gui.show_screen('sale_order_form');
			});
            var back_$el = this.$el.find('.back');
            back_$el.off('click');
            back_$el.on('click',function() {
                self.ask_manager_ask_pin().then(function(approver){
                self.gui.show_screen('sale_order_return_form', {
                        'approver': approver,
                    });
				});
            });

//            if(odoo.session_info.sale_type == 'dropship')
//                back_$el.hide();
//            else
//                back_$el.show();

            if(self.pos.get_order().amount)
                self.pos.get_order().destroy()

            if (self.pos.db.order_by_id){
                this.render_list(_.values(self.pos.db.order_by_id).sort((a,b)=>b.id-a.id) , undefined);
            }
            else {
                this.render_list([] , undefined);
            }

			this.$el.find('.order_search').val('');
			this.$el.find('.order_search').focus();
			this.$el.find('.order_search').off('blur');
			this.$el.find('.order_search').off('keypress');
			this.$el.find('.order_search').keypress(function(event) {
                if(event.target && event.target.tagName.toUpperCase() == 'INPUT') {
                    if(event.keyCode == 13) {
                        event.preventDefault();
                        return $(event.target).blur();
                    }
                }
			});
			this.$el.find('.order_search').off('change');
			this.$el.find('.order_search').on('blur', function() {
			    this.value = this.value.trim();
			    var so_no = this.value;
                if (this.value.length != 0){
                    self.order_request(so_no).then(function(result){
                        self.chrome.loading_hide();
                        if (result.orders){
                            self.render_list(result.orders, undefined);
                            var orderlist = self.$el.find('.sale-order-line');
                            if (orderlist.length == 1){
                                orderlist[0].click();
                            }
                            return;
                        }
                        else{
                            self.render_list([], undefined);
                            self.gui.show_popup('alert', {
                                'title': _t('Order Not Found'),
                                'body': so_no +
                                        _t(' not found '),
                            });
                            return;
                        }
                    }, function(err){
                        self.chrome.loading_hide();
                        console.error(err);
                    });
                }
                else{
                    self.render_list(_.values(self.pos.db.order_by_id).sort((a,b)=>b.id-a.id) , undefined);
                }
			});

			this.$el.find('.sale-order-list-contents').off('click', '.sale-order-line');
			this.$el.find('.sale-order-list-contents').on('click', '.sale-order-line', function(event) {
				self.line_select(event, $(this), parseInt($(this).data('id')));
			});
			self.refresh_sale_order_list();
        },
        is_refresh_sale_order: false,
        refresh_sale_order_list: function(){
            var self = this;
            if(!self.is_refresh_sale_order){
                new Model('sale.order')
                .query(['name', 'quotation_no', 'partner_id', 'date_order', 'amount_total', 'state'])
                .filter([
                    ['type_sale_ofm', '=', (odoo.session_info.sale_type == 'dropship')],
                    ['branch_id','=', self.pos.branch.id],
                    ['state','in', ['draft', 'sent']]
                ])
                .limit(100)
                .all({'timeout':3000, 'shadow': true})
                .then(function(orders){
                    if(orders && orders.length){
                        self.pos.db.order_by_id = {};
                        orders.forEach(function(order){
                            self.pos.db.order_by_id[order.id] = order;
                        });
                        self.render_list(_.values(self.pos.db.order_by_id).sort((a,b)=>b.id-a.id) , undefined);
                    }
                }, function(err,event){
                    console.error(err);
                    event.preventDefault();
                }).always(function(){
                    self.is_refresh_sale_order = false;
                });
            }
        },
		close: function() {
			this._super();
		},
    });
	gui.define_screen({name: 'sale_order_list', widget:SaleOrderListScreenWidget});


    /* --------- The Saler Order Form, Order Widget --------- */

    // Displays the current Order.

    var SaleOrderWidget = PosBaseWidget.extend({
        template:'SaleOrderWidget',
        init: function(parent, options) {
            var self = this;
            this._super(parent,options);

            this.pos.bind('change:selectedOrder', this.change_selected_order, this);

            if(options.allow_number)
                this.allow_number = options.allow_number;
            if(options.enter_to_blur)
                this.enter_to_blur = options.enter_to_blur;

            if (this.pos.get_order()) {
                this.bind_order_events();
            }
        },
        orderline_onchange_input: function(orderline, event){
            var value = orderline.sale_node.querySelector('.ordered > input').value;

            if(orderline && orderline.order && orderline.order.is_calculated_promotion) {
                document.getElementsByClassName("discount_see").discount_see.value = '';
                orderline.order.amount_discount_text = '';
                orderline.order.reverse_promotions();
            }
            
            orderline.quantity = value;
            orderline.quantityStr = value + '';

            orderline.order.save_to_db();
            orderline.order.calculate_shipping_fee_by_order();
            this.orderline_change(orderline);
        },
        change_selected_order: function() {
            if (this.pos.get_order()) {
                this.bind_order_events();
                this.renderElement();
            }
        },
        orderline_add: function(){
            this.renderElement('and_scroll_to_bottom');
        },
        orderline_remove: function(line){
            this.remove_orderline(line);
            this.update_summary();
        },
        orderline_change: function(line){
            this.rerender_orderline(line);
            this.update_summary();
        },
        bind_order_events: function() {
            var order = this.pos.get_order();
                order.unbind('change:client', this.update_summary, this);
                order.bind('change:client',   this.update_summary, this);
                order.unbind('change',        this.update_summary, this);
                order.bind('change',          this.update_summary, this);

            var lines = order.orderlines;
                lines.unbind('add',     this.orderline_add,    this);
                lines.bind('add',       this.orderline_add,    this);
                lines.unbind('remove',  this.orderline_remove, this);
                lines.bind('remove',    this.orderline_remove, this);
                lines.unbind('change',  this.orderline_change, this);
                lines.bind('change',    this.orderline_change, this);

        },
        render_orderline: function(orderline){
            var el_str  = QWeb.render('SaleOrderline',{widget:this, line:orderline});
            var el_node = document.createElement('div');
                el_node.innerHTML = _.str.trim(el_str);
                el_node = el_node.childNodes[0];
                el_node.orderline = orderline;
                /*el_node.addEventListener('click',this.line_click_handler);*/
                el_node.querySelector('.ordered > input').addEventListener('change', this.orderline_onchange_input.bind(this, orderline))
                el_node.querySelector('.ordered > input').addEventListener('keypress', this.enter_to_blur);
                el_node.querySelector('.ordered > input').addEventListener('keypress', this.allow_number);

            var trash_icon = el_node.querySelector('.orderline-trash');
            if(trash_icon){
                trash_icon.addEventListener('click', (function() {
                    if(orderline && orderline.order && orderline.order.is_calculated_promotion) {
                        document.getElementsByClassName("discount_see").discount_see.value = '';
                        orderline.order.amount_discount_text = '';
                        orderline.order.reverse_promotions();
                    }
                    this.pos.get_order().remove_orderline(orderline);
                    this.pos.get_order().calculate_shipping_fee_by_order();
                    this.update_summary();
                }.bind(this)));
            }

            orderline.sale_node = el_node;
            return el_node;
        },
        remove_orderline: function(order_line){
            if(this.pos.get_order().get_orderlines().length === 0){
                this.renderElement();
            }
            else{
                order_line.sale_node.parentNode.removeChild(order_line.sale_node);
            }
        },
        rerender_orderline: function(order_line){
            var node = order_line.sale_node;
            var replacement_line = this.render_orderline(order_line);
            node.parentNode.replaceChild(replacement_line,node);
        },
        // overriding the openerp framework replace method for performance reasons
        replace: function($target){
            this.renderElement();
            var target = $target[0];
            target.parentNode.replaceChild(this.el,target);
        },
        renderElement: function(scrollbottom){
            var order  = this.pos.get_order();
            if (!order) {
                return;
            }
            var orderlines = order.get_orderlines();

            var el_str  = QWeb.render('SaleOrderWidget',{widget:this, order:order, orderlines:orderlines});

            var el_node = document.createElement('div');
                el_node.innerHTML = _.str.trim(el_str);
                el_node = el_node.childNodes[0];


            var list_container = el_node.querySelector('.orderlines');
            for(var i = 0, len = orderlines.length; i < len; i++){
                var orderline = this.render_orderline(orderlines[i]);
                list_container.appendChild(orderline);
            }

            if(this.el && this.el.parentNode){
                this.el.parentNode.replaceChild(el_node,this.el);
            }
            this.el = el_node;
            this.update_summary();

            if(scrollbottom){
                this.el.querySelector('.order-scroller').scrollTop = 100 * orderlines.length;
            }
        },
        get_total_value_with_discount_see: function(){
            //copy of update summary that returns total_value
            var order = this.pos.get_order();
            if (!order.get_orderlines().length) {
                return;
            }
            var total_before_discount = 0,
                total_discount = 0,
                shipping_fee = 0,
                total_non_vat = 0,
                total_vat_excluded = 0,
                total_vat_included = 0,
                total_vat_amount = 0,
                change_rounding = 0,
                total = 0;

            if(order){
                total = order.get_total_with_tax();

                total_before_discount = order.get_subtotal_without_discount();

                total_discount = Math.abs(total - total_before_discount);

                var total_products = order.get_total_products_vat_nonvat();

                total_non_vat = total_products.nonvat;
                total_vat_included = total_products.vat_included;
                total_vat_excluded = total_products.vat_excluded;
                total_vat_amount = total_products.vat_amount;

                if(order.amount_delivery_fee_by_order){
                    shipping_fee += order.amount_delivery_fee_by_order;
                    total_before_discount += order.amount_delivery_fee_by_order;
                    total += order.amount_delivery_fee_by_order;
                }
            }

            return total_before_discount;
        },
        update_summary: function(){
            var order = this.pos.get_order();
            if (!order.get_orderlines().length) {
                return;
            }
            var total_before_discount = 0,
                total_discount = 0,
                total_discount_see = 0,
                shipping_fee = 0,
                total_non_vat = 0,
                total_vat_excluded = 0,
                total_vat_included = 0,
                total_vat_amount = 0,
                change_rounding = 0,
                total = 0;

            if(order){
                total = order.get_total_with_tax();

                total_before_discount = order.get_subtotal_without_discount();

                total_discount = Math.abs(total - total_before_discount);
                if(order.amount_discount_by_order && order.amount_discount_by_order > 0){
                    total_discount_see = order.amount_discount_by_order;
                    total_discount -= total_discount_see;
                }

                var total_products = order.get_total_products_vat_nonvat();

                total_non_vat = total_products.nonvat;
                total_vat_included = total_products.vat_included;
                total_vat_excluded = total_products.vat_excluded;
                total_vat_amount = total_products.vat_amount;

                if(order.amount_delivery_fee_by_order){
                    shipping_fee += order.amount_delivery_fee_by_order;
                    //total_before_discount += order.amount_delivery_fee_by_order;
                    total += order.amount_delivery_fee_by_order;
                }

                if(order.amount_delivery_fee_special){
                    shipping_fee += order.amount_delivery_fee_special;
                    //total_before_discount += order.amount_delivery_fee_special;
                    total += order.amount_delivery_fee_special;
                }

                if(!(this.product_taxes &&this.product_taxes.length)){
                    var vat_product = posmodel.db.products.find(product => product.taxes_id.length);
                    if(vat_product)
                        this.product_taxes = vat_product.taxes_id;
                    else
                        this.product_taxes = [];
                }
                
                if(order.get_orderlines().length && this.product_taxes.length){
                    if(shipping_fee){
                        var amount = order.get_orderlines()[0].get_all_prices_by_subtotal(shipping_fee, {taxes_id: this.product_taxes});
                        total_vat_excluded += amount.priceWithoutTax;
                        total_vat_amount += amount.tax;
                    }
                }
            }

            this.el.querySelector('.summary .total .subentry .total_before_discount_value').textContent = this.format_currency(total_before_discount);
            this.el.querySelector('.summary .total .subentry .total_discount_value').textContent = this.format_currency(-Math.abs(total_discount));
            this.el.querySelector('.summary .total .subentry .total_discount_see_value').textContent = this.format_currency(-Math.abs(total_discount_see));
            this.el.querySelector('.summary .total .subentry .shipping_fee').textContent = this.format_currency(shipping_fee);
            this.el.querySelector('.summary .total .subentry .total_non_vat_value').textContent = this.format_currency(total_non_vat);
            this.el.querySelector('.summary .total .subentry .total_vat_excluded_value').textContent = this.format_currency(total_vat_excluded);
            this.el.querySelector('.summary .total .subentry .total_vat_amount_value').textContent = this.format_currency(total_vat_amount);

            this.el.querySelector('.summary .total > .total_value').textContent = this.format_currency(total);
        },
    });


    /* -------- The Sale Order Form Screen -------- extend from ProductScreenWidget*/
    var SaleOrderFormScreenWidget = screens.ScreenWidget.extend({
        template:'SaleOrderFormScreenWidget',
        /* standard function */
        start: function(){

            var self = this;

            this.order_widget = new SaleOrderWidget(this, {
                allow_number: this.allow_number,
                enter_to_blur: this.enter_to_blur,
            });
            this.order_widget.replace(this.$el.find('.placeholder-SaleOrderWidget'));

            this.product_list_widget = new screens.ProductListWidget(this,{
                click_product_action: function(product){ self.click_product(product); },
                product_list: this.pos.db.get_product_by_category(0)
            });
            this.product_list_widget.replace(this.$el.find('.placeholder-SaleProductListWidget'));

            this.product_categories_widget = new screens.ProductCategoriesWidget(this,{
                product_list_widget: this.product_list_widget,
            });
            this.product_categories_widget.replace(this.$el.find('.placeholder-SaleProductCategoriesWidget'));


            this.calculate_promotion_$el = this.$el.find('.calculate_promotion');
            this.save_sale_order_$el = this.$el.find('.save_sale_order');
            this.customer_action_$el = this.$el.find('.set-customer');
            this.back_$el = this.$el.find('.back');
            this.check_quantity_$el = this.$el.find('.check-quantity');
            this.print_qu_$el = this.$el.find('.print-qu');
            this.search_t1c_$el = this.$el.find('.search_t1c');
            this.bind_button_event();

            //destroy the currently cache
            if(odoo.session_info && 'sale_type' in odoo.session_info){
                this.pos.get_order().destroy();
            }
        },
        bind_button_event: function(){
            var self = this;
            this.calculate_promotion_$el.off('click');
            this.calculate_promotion_$el.on('click', function(event){
                var order = self.pos.get_order();
                if(order && order.get_orderlines().length){
                    self.pos.get_order().doing_promotion = true;
                    self.pos.get_order().apply_promotions();
                    self.pos.get_order().doing_promotion = undefined;
                    self.order_widget.renderElement();
                }
            });

            this.save_sale_order_$el.off('click');
            this.save_sale_order_$el.on('click', function(event){
                var order = self.pos.get_order();
                if(order && order.get_orderlines().length){
                    self.submit_order();
                }
            });

            this.customer_action_$el.off('click');
            this.customer_action_$el.on('click', function(event){
                self.pos.gui.show_screen('clientlistapi');
            });

            this.back_$el.off('click');
            this.back_$el.on('click', function(event){
                self.pos.get_order().destroy();
                self.gui.show_screen('sale_order_list');
            });

            this.check_quantity_$el.off('click');
            this.check_quantity_$el.on('click', function(event){
                self.pos.chrome.loading_show();
                self.pos.chrome.loading_message('กรุณารอสักครู่ ระบบกำลังบันทึกข้อมูล', 0.5);
                self.call_api_check_qty().always(function(){
                    self.pos.chrome.loading_hide();
                    self.render_order_date_detail();
                });
            });

            this.print_qu_$el.off('click');
            this.print_qu_$el.on('click', function(event){
                self.pos.chrome.loading_show();
                self.pos.chrome.loading_message('กรุณารอสักครู่ ระบบกำลังบันทึกข้อมูล', 0.5);
                self.call_print_qu().always(function(){
                    self.pos.chrome.loading_hide();
                    self.render_order_date_detail();
                });
            });

            this.search_t1c_$el.off('click');
            this.search_t1c_$el.on('click', function(event){
                self.click_set_card();
            });
        },
        click_set_card: function(){
            var order = this.pos.get_order();
            /* Condition for Check Online state */
            var condition = navigator.onLine ? "online" : "offline";
            if (condition === 'online'){
                this.gui.show_screen('cardlist');
            } else {
                /* if pos status is offline show popup! */
                this.gui.show_popup('card_offline',{
                    title: "Alert! No internet connection",
                    confirm: function() {
                         var value = this.$el.find('input').val();
                         order.membercard.the_one_card_no = value;
                         order.t1c_set = true;
                         order.pos_offline = true;
                         $('.member_search').text(value);
                         $('.member-the_one_card_no').text(value);
                         order.save_to_db();
                    },
                });

            }
        },
        handle_on_keypress_internal_note: function(value){
            var order = this.pos.get_order();
            if(order.note != value){
                order.note = value;
                order.save_to_db();
            }
        },
        handle_on_keypress_shipping_fee: function(value){
            var order = this.pos.get_order();
            if(order.amount_delivery_fee_by_order != value){
                order.amount_delivery_fee_by_order = value;
                order.save_to_db();
            }
        },
        handle_on_keypress_discount_see: function(value){
            var order = this.pos.get_order();
            if(order.amount_discount_text != value){

                order.amount_discount_text = value;

                order.add_discount_f_see();
                order.save_to_db();
            }
        },
        click_product: function(product) {
           if(product.to_weight && this.pos.config.iface_electronic_scale){
               this.gui.show_screen('scale',{product: product});
           }else{
               this.pos.get_order().add_product(product);
           }
        },
        show: function(reset){
            var self = this;
            this._super();
            if (reset) {
                this.product_categories_widget.reset_category();
            }
            if (this.pos.config.iface_vkeyboard && this.chrome.widget.keyboard) {
                this.chrome.widget.keyboard.connect($(this.el.querySelector('.searchbox input')));
            }
            if(odoo && odoo.session_info && 'sale_type' in odoo.session_info){
                this.render_order_date_detail();
                this.render_customer_sale_action();
                this.render_note_and_shipping_fee();
                this.render_the_one_card_detail();
            }
            this.order_widget.update_summary();
        },
        close: function(){
            this._super();
            if(this.pos.config.iface_vkeyboard && this.chrome.widget.keyboard){
                this.chrome.widget.keyboard.hide();
            }
        },
        render_the_one_card_detail: function(){
            var self = this;
            var placeholder = this.$el.find('.placeholder-sale-order-form-the-one-card-info');
            placeholder.empty();
            this.the_one_card_detail = $(QWeb.render('SaleTheOneCardDetail',{widget:this, order: this.pos.get_order()}));
            this.the_one_card_detail.appendTo(placeholder);
        },
        render_note_and_shipping_fee: function(){
            var self = this;
            var placeholder = this.$el.find('.placeholder-order-note-shipping-free');
            placeholder.empty();
            this.note_and_shipping_fee = $(QWeb.render('SaleOrderFromNoteShippingFee',{widget:this}));

            var note_$el = this.note_and_shipping_fee.find('.internal_note');
            note_$el.off('change paste keyup keypress keydown');
            note_$el.on('change paste keyup keypress keydown', function(event){
                self.handle_on_keypress_internal_note((this.value || '').trim());
            });
            this.note_and_shipping_fee.appendTo(placeholder);

            var discount_see_$el = this.note_and_shipping_fee.find('.discount_see');
            discount_see_$el.val(this.pos.get_order().amount_discount_text);
            discount_see_$el.off('change paste keyup keypress keydown');
            var custom_key = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", ".", "%"];
            discount_see_$el.on('keypress', (event)=>this.allow_with_custom(event, custom_key));
            discount_see_$el.on('keypress', this.enter_to_blur);
            discount_see_$el.on('blur', function(event){
                var discount = (discount_see_$el[0].value || '').trim();
                // remove multiple percentage character
                if(discount.split('%').length > 1){
                    discount = discount.split('%')[0] + '%';
                    discount_see_$el[0].value = discount;
                }
                // check discount see % is greater than 100
                if(discount.indexOf('%') >= 0){
                    if(discount.indexOf('%') == 0)
                        discount = '';
                    else{
                        discount = parseFloat(discount.split('%')[0]);
                        if(discount > 100)
                            discount = 100
                        discount = discount + '%';
                    }
                    discount_see_$el[0].value = discount;
                }
                var prev_amount_discount_text = self.pos.get_order().amount_discount_text || '';
                if (discount != prev_amount_discount_text) {
                    var manager_pin = self.ask_manager_ask_pin();
                    manager_pin.then(function(approver){
                        var total_value = self.order_widget.get_total_value_with_discount_see();
                        if(discount.indexOf('%') == -1)
                            total_value -= parseFloat(discount);
                        if (total_value < 0) {
                            discount_see_$el[0].value = prev_amount_discount_text;
                            self.gui.show_popup('alert', {
                                'title': 'Alert',
                                'body': _t('ใส่ส่วนลดเกินมูลค่าของสินค้า กรุณาตรวจสอบใหม่')
                            });
                        }
                        else {
                            self.handle_on_keypress_discount_see(discount);
                            self.order_widget.update_summary();
                            var order = self.pos.get_order();
                            order.discount_approval_manager = approver.id;
                            order.discount_approval_time = approver.datetime;
                            order.save_to_db();
                        }
                    }, function(){
                        discount_see_$el[0].value = prev_amount_discount_text;
                    });
                }
            });

            var shipping_fee_$el = this.note_and_shipping_fee.find('.shipping_fee');
            shipping_fee_$el.off('change paste keyup keypress keydown');
            shipping_fee_$el.on('keypress', this.allow_number);
            shipping_fee_$el.on('keypress', this.enter_to_blur);
            shipping_fee_$el.on('blur', function(event){
                self.order_widget.update_summary();
            });
            shipping_fee_$el.on('change paste keyup keypress keydown', function(event){
                self.handle_on_keypress_shipping_fee(parseInt((this.value || '').trim()));
            });
        },
        render_customer_sale_action: function(){
            var self = this;

            this.customer_action_$el.empty();
            $(QWeb.render('CustomerAction',{
                widget:this,
            })).appendTo(this.customer_action_$el);

            var customer_info_el =  this.$el.find('.placeholder-sale-order-form-customer-info');
            customer_info_el.empty();
            var customer_info = {}, full_address, full_invoice_address, full_shipping_address;
            var customer = self.pos.get_client();
            if(customer){
                customer_info.name = customer.name;
                full_address = customer.full_address;
                customer_info.full_invoice_address = customer.full_invoice_address;
                customer_info.full_delivery_address = customer.full_delivery_address;

                customer_info.delivery_method = 'Instore';
                if(odoo.session_info && 'sale_type' in odoo.session_info && odoo.session_info.sale_type == 'dropship')
                    customer_info.delivery_method = 'Dropship';

                customer_info.payment_term = 'Immediate Payment'
                customer_info.max_aging = '-';
                customer_info.aging_balance = '-';
                if(customer.customer_payment_type == 'credit'){
                    if(customer.property_payment_term_id)
                        customer_info.payment_term =  customer.property_payment_term_id[1];
                    else
                        customer_info.payment_term = '-'
                    customer_info.max_aging = customer.max_aging;
                    customer_info.aging_balance = customer.aging_balance;
                }
                customer_info.trust = self.pos.db.trust_level[customer.trust];
            }

            this.customer_sale_action = $(QWeb.render('CustomerSaleDetail',{
                widget:this,
                customer: customer_info,
                full_address: full_address,
            }));

            this.customer_sale_action.appendTo(customer_info_el);

            var customer_detail_el =  this.$el.find('.placeholder-customer-detail');
            customer_detail_el.empty();

            var data = [{
                field: 'Delivery Method :',
                detail: customer_info.delivery_method,
            },{
                field: 'Payment Terms :',
                detail: customer_info.payment_term || '',
            },{
                field: 'Credit Limit :',
                detail: self.format_currency_no_symbol(customer_info.max_aging) || '',
            },{
                field: 'Credit Balance :',
                detail: self.format_currency_no_symbol(customer_info.aging_balance) || '',
            },{
                field: 'Degree of Trust :',
                detail: customer_info.trust || '',
            }];

            this.customer_detail = this.render_record_info(data);
            this.customer_detail.appendTo(customer_detail_el)
        },
        render_record_info: function(data){
            if(!(data instanceof Array))
                data = [data]
            return $(QWeb.render('RecordInfoOnTable',{widget:this, data:data}));
        },
        render_order_date_detail: function(){
            var order = this.pos.get_order();
            if(order){
                if(!order.formatted_expiration_date || !order.formatted_validation_date){
                    order.initialize_validation_date();
                }
                var data = [{
                    field: 'Quotation No.',
                    detail: order.quotation_no || order.so_name || 'New',
                },{
                    field: 'Order Date :',
                    detail: order.formatted_validation_date.split(' ')[0],
                },{
                    field: 'Expiration Date :',
                    detail: order.formatted_expiration_date.split(' ')[0],
                }];

                this.$el.find('.placeholder-order-date-detail').empty();
                this.order_date_detail = this.render_record_info(data);
                this.order_date_detail.appendTo(this.$el.find('.placeholder-order-date-detail'))
            }
        },
        request_sale_new_tab: function(order_id){
            if(order_id){
                var url = '/web#id=' + order_id + '&';
                if(odoo && odoo.session_info && 'sale_type' in odoo.session_info && odoo.session_info.sale_type == 'dropship'){
                    url += this.pos.menu_ofm_quotations;
                }
                else{
                    url += this.pos.menu_sale_quotations;
                }
                window.open(url ,'_blank');
            }
        },
        submit_order: function(force_validation = false){
            var self = this;
            var order = this.pos.get_order();
            if(order){
                if(self.check_submit(force_validation)){
                    self.pos.chrome.loading_show();
                    self.pos.chrome.loading_message('กรุณารอสักครู่ ระบบกำลังบันทึกข้อมูล', 0.5);

                    self.call_api_check_qty(self).then(function(order_ids){
                        //console.log(order_ids);
                        if(order_ids && order_ids.length){
                            order_ids.forEach(function(order_id){
                                if(order_id.id in self.pos.db.order_by_id){
                                    self.pos.db.order_by_id[order_id.id].quotation_no = order_id.quotation_no;
                                    self.pos.db.order_by_id[order_id.id].so_name = order_id.name;
                                }
                                else{
                                    self.pos.db.order_by_id[order_id.id] = order_id;
                                }
                                self.request_sale_new_tab(order_id.id);
                            });
                            self.pos.get_order().destroy();
                            self.gui.back();
                        }
                    }).always(function(){
                        self.pos.chrome.loading_hide();
                    });
                }
            }
        },
        check_sale_order: function(){
            var self = this;
            var order = this.pos.get_order();
            if(order.get_orderlines().length == 0)
                return false;
            var client = this.pos.get_client();
            if(!(client && client.id)){
                this.pos.gui.show_popup('confirm', {
                    'title': 'เลือกรายชื่อลูกค้า',
                    'body': 'กรุณาเลือกรายชื่อลูกค้าเพื่อทำรายการ',
                    confirm: function () {
                        self.pos.gui.show_screen('clientlistapi');
                    },
                });
                return false;
            }
            if(client.customer_payment_type == 'credit'){
                if(!client.property_payment_term_id){
                    this.pos.gui.show_popup('alert', {
                        'title': 'Alert',
                        'body': 'กรุณาแก้ข้อมูลระยะเวลาการชำระของลูกค้า '+ client.name,
                    });
                    return false;
                }
            }
            return true;
        },
        check_submit: function(force_validation){
            var self = this;
            var order = this.pos.get_order();
            var show_warning = false;
            if(!self.check_sale_order()){
                return false;
            }
            if (order.get_total_with_tax() <= 0) {
                this.pos.gui.show_popup('zero_with_tax_popup', {
                    'title': 'Warning',
                    'body': 'ยอดรวมราคาของสินค้าทั้งหมดเป็น 0 ไม่สามารถทำรายการได้ กรุณาตรวจสอบใหม่อีกครั้ง',
                    'confirm_title': 'ตกลง',
                    'cancel_title': 'Cancel',
                });
                return false;  
            }
            var promotion_lines = _.filter(order.orderlines.models, function(line) {
                return line.promotion_id;
            });
            if (order.is_calculated_promotion && !Boolean(promotion_lines.length)) {
                //order has status is_calculated_promotion but the list of promotion 
                //lines are empty (we don't count the lines for special discount)
                //this caused a problem where the user will input a special discount 
                //and a warning will not show even if they didnt click promotion when one exists
                show_warning = true;
            }

            if(!force_validation && (!order.is_calculated_promotion || show_warning)){
                this.pos.gui.show_popup('confirm_promotion', {
                    'title': 'ยังไม่ได้คำนวนโปรโมชั่น',
                    'body': 'อาจส่งผลให้ลูกค้าไม่ได้โปรโมชั่น<br/>จะดำเนินการคิดโปรโมชั่น "ตกลง" หรือ<br/>กด "ข้าม" เพื่อข้ามขั้นตอนการให้โปรโมชั่น',
                    'confirm_title': 'ตกลง',
                    'cancel_title': 'ข้าม',
                    confirm: function(){
                        self.pos.get_order().doing_promotion = true;
                        self.pos.get_order().apply_promotions();
                        self.pos.get_order().doing_promotion = undefined;
                        self.submit_order();
                    },
                    cancel:  function(){
                        self.submit_order('skip_promotion');
                    },
                });
                return false;
            }
            return true;
        },
        push_sale_order: function(){
            var self = this;
            var order = this.pos.get_order();
            var deferred = $.Deferred();
            if(order){
                self.pos.db.add_order(order.export_as_JSON());

                self.pos._save_to_server(self.pos.db.get_orders()).then(function(server_ids){
                    deferred.resolve(server_ids);
                }, function(err, event){
                    console.error(err);
                    event.preventDefault();
                    if(err.data && err.data.type&& err.data.type == "xhrtimeout"){
                        /*show popup*/
                        self.pos.gui.show_popup('alert', {
                            'title': 'Alert',
                            'body': 'กรุณาลองใหม่อีกครั้ง',
                        });
                    }
                    else if(err.data && err.data.type&& err.data.type == "xhrerror"){
                        self.pos.gui.show_popup('alert', {
                            'title': 'Alert',
                            'body': 'กรุณาลองใหม่อีกครั้ง',
                        });
                    }
                    deferred.resolve();
                });
            }
            else{
                deferred.reject('no order');
            }
            return deferred;
        },
        call_api_check_qty: function(){
            var self = this;
            var deferred = $.Deferred();
            if(!self.check_sale_order()){
                deferred.resolve();
            }
            else{
                self.push_sale_order().then(function(order_ids){
                    if(order_ids && order_ids.length){
                        order_ids.forEach(function(order_id){
                            if(order_id.id in self.pos.db.order_by_id){
                                self.pos.db.order_by_id[order_id.id].quotation_no = order_id.quotation_no;
                                self.pos.db.order_by_id[order_id.id].so_name = order_id.name;
                            }
                            else{
                                self.pos.db.order_by_id[order_id.id] = order_id;
                            }
                            //self.request_sale_new_tab(order_id.id);
                        });
                        self.pos.chrome.loading_message('กรุณารอสักครู่ ระบบกำลังเช็คสินค้า', 0.7);

                        new Model('sale.order').call('call_api_check_qty_from_ui', [{
                            'order_id': order_ids[0].id,
                        }]).then(function(response){
                            var warning = response.warning;
                            var orders = response.records;
                            var found = false;

                            orders.forEach(function(order){
                                if(order.id == order_ids[0].id)
                                    found = true;
                                self.pos.db.order_by_id[order.id] = order;
                            });

                            if(found && orders.length){
                                self.pos.set_sale_order_from_db(order_ids[0].id);

                                if(warning && warning.length){
                                    warning.forEach(function(message){
                                        web_client.notification_manager.warn(message.body, message.header, true);
                                    });
                                }
                                if(self.pos.get_order().get_orderlines().find((line)=>line.is_danger)){
                                    deferred.resolve();
                                }
                                else{
                                    deferred.resolve([orders[0]]);
                                }
                            }
                            else{
                                deferred.resolve();
                            }

                        },function(err){
                            console.error(err);
                            deferred.resolve();
                        });
                    }
                    else{
                        deferred.resolve();
                    }
                });
            }
            return deferred;
        },
        call_print_qu: function(){
            var self = this;
            var deferred = $.Deferred();
            if(!self.check_sale_order()){
                deferred.resolve();
            }
            else{
                self.push_sale_order().then(function(order_ids){
                    if(order_ids && order_ids.length){
                        order_ids.forEach(function(order_id){
                            if(order_id.id in self.pos.db.order_by_id){
                                self.pos.db.order_by_id[order_id.id].quotation_no = order_id.quotation_no;
                                self.pos.db.order_by_id[order_id.id].so_name = order_id.name;
                            }
                            else{
                                self.pos.db.order_by_id[order_id.id] = order_id;
                            }
                            //self.request_sale_new_tab(order_id.id);
                        });
                        self.pos.chrome.loading_message('กรุณารอสักครู่ ระบบกำลังดึงรายงาน', 0.7);

                        self.pos.chrome.do_action('ofm_so_ext.qu_form_jasper',{additional_context:{
                            active_ids:[order_ids[0].id],
                            active_model:'sale.order'
                        }}).always(function(){
                            deferred.resolve();
                        });
                    }
                    else{
                        deferred.resolve();
                    }
                });
            }
            return deferred;
        },
    });
    gui.define_screen({name:'sale_order_form', widget: SaleOrderFormScreenWidget});

    /*--------------------------------------*\
     |         THE CLIENT LIST              |
    \*======================================*/

    // The clientlist displays the list of customer,
    // and allows the cashier to create, edit and assign
    // customers.

    /* -------- ClientListAPIScreenWidget  -------- clone from ClientListScreenWidget */
    var ClientListAPIScreenWidget = screens.ScreenWidget.extend({
        template: 'ClientListAPIScreenWidget',

        init: function(parent, options){
            this._super(parent, options);
            this.partner_cache = new screens.DomCache();
        },

        auto_back: true,

        show: function(){
            var self = this;
            this._super();

            this.renderElement();
            this.details_visible = false;
            this.old_client = this.pos.get_order().get_client();

            this.$el.find('.back').click(function(){
                self.gui.back();
            });

            this.$el.find('.next').click(function(){
                self.save_changes();
                self.gui.back();
            });

            this.$el.find('.new-customer').click(function(){
                self.display_client_details('edit',{
                    'country_id': self.pos.company.country_id,
                });
            });

            //var partners = this.pos.db.get_partners_sorted(1000);
            //this.render_list(partners);
            this.render_list([]);

            //this.reload_partners();

            if( this.old_client ){
                this.display_client_details('show',this.old_client,0);
            }

            this.$el.find('.client-list-contents').delegate('.client-line','click',function(event){
                self.line_select(event,$(this),parseInt($(this).data('id')));
            });

            var search_timeout = null;

            if(this.pos.config.iface_vkeyboard && this.chrome.widget.keyboard){
                this.chrome.widget.keyboard.connect(this.$el.find('.searchbox input'));
            }

            this.$el.find('.searchbox input').on('keypress', this.enter_to_blur);
            this.$el.find('.searchbox input').on('blur',function(event){
                var value = this.value || '';
                value = value.trim()
                if(value && value.length){
                    self.perform_search(value);
                }
            });

            this.$el.find('.searchbox .search-clear').click(function(){
                self.clear_search();
            });
        },
        hide: function () {
            this._super();
            this.new_client = null;
        },
        barcode_client_action: function(code){
            if (this.editing_client) {
                this.$el.find('.detail.barcode').val(code.code);
            } else if (this.pos.db.get_partner_by_barcode(code.code)) {
                var partner = this.pos.db.get_partner_by_barcode(code.code);
                this.new_client = partner;
                this.display_client_details('show', partner);
            }
        },
        api_get_partner_info: function(query){
            var self = this;
            var deferred = $.Deferred();
            if(query && query.length){
                self.pos.chrome.loading_show()
                self.pos.chrome.loading_message('กรุณารอสักครู่ ระบบกำลังดึงข้อมูล', 0.5);

                new Model('res.partner').call('get_partner_info', [{key:query}]).then(function(result){
                    deferred.resolve(result);
                },function(err, event){
                    console.error(err);
                    event.preventDefault();
                }).always(function(){
                    self.pos.chrome.loading_hide();
                });
            }
            else{
                deferred.reject();
            }
            return deferred;
        },
        perform_search: async function(query){
            var customers;
            if(query.length){
                customers = await this.api_get_partner_info(query);
                this.pos.db.add_partners(customers);
                this.display_client_details('hide');
                //console.log('customers', customers)
                // if (customers.length === 1){
                //     this.new_client = this.pos.db.partner_by_id[customers[0].id];
                //     this.save_changes();
                //     this.gui.back();
                // }
                this.render_list(customers);
            }else{
                //customers = this.pos.db.get_partners_sorted();
                this.render_list([]);
            }
        },
        clear_search: function(){
            //var customers = this.pos.db.get_partners_sorted(1000);
            //this.render_list(customers);
            this.render_list([]);
            this.$el.find('.searchbox input')[0].value = '';
            this.$el.find('.searchbox input').focus();
        },
        render_list: function(partners){
            var contents = this.$el[0].querySelector('.client-list-contents');
            contents.innerHTML = "";
            for(var i = 0, len = Math.min(partners.length,1000); i < len; i++){
                var partner    = partners[i];
                var clientline = this.partner_cache.get_node(partner.id);
                if(!clientline){
                    var clientline_html = QWeb.render('ClientLineAPI',{widget: this, partner:partners[i]});
                    var clientline = document.createElement('tbody');
                    clientline.innerHTML = clientline_html;
                    clientline = clientline.childNodes[1];
                    this.partner_cache.cache_node(partner.id,clientline);
                }
                if( partner === this.old_client ){
                    clientline.classList.add('highlight');
                }else{
                    clientline.classList.remove('highlight');
                }
                contents.appendChild(clientline);
            }
        },
        save_changes: function(){
            var self = this;
            var order = this.pos.get_order();
            if( this.has_client_changed() ){
                var default_fiscal_position_id = _.find(this.pos.fiscal_positions, function(fp) {
                    return fp.id === self.pos.config.default_fiscal_position_id[0];
                });
                if ( this.new_client && this.new_client.property_account_position_id ) {
                    order.fiscal_position = _.find(this.pos.fiscal_positions, function (fp) {
                        return fp.id === self.new_client.property_account_position_id[0];
                    }) || default_fiscal_position_id;
                } else {
                    order.fiscal_position = default_fiscal_position_id;
                }

                order.set_client(this.new_client);
            }
        },
        has_client_changed: function(){
            if( this.old_client && this.new_client ){
                return this.old_client.id !== this.new_client.id;
            }else{
                return !!this.old_client !== !!this.new_client;
            }
        },
        toggle_save_button: function(){
            var $button = this.$el.find('.button.next');
            if (this.editing_client) {
                $button.addClass('oe_hidden');
                return;
            } else if( this.new_client ){
                if( !this.old_client){
                    $button.text(_t('Set Customer'));
                }else{
                    $button.text(_t('Change Customer'));
                }
            }else{
                $button.text(_t('Deselect Customer'));
            }
            $button.toggleClass('oe_hidden',!this.has_client_changed());
        },
        line_select: function(event,$line,id){
            var partner = this.pos.db.get_partner_by_id(id);
            this.$el.find('.client-list .lowlight').removeClass('lowlight');
            if ( $line.hasClass('highlight') ){
                $line.removeClass('highlight');
                $line.addClass('lowlight');
                this.display_client_details('hide',partner);
                this.new_client = null;
                this.toggle_save_button();
            }else{
                this.$el.find('.client-list .highlight').removeClass('highlight');
                $line.addClass('highlight');
                var y = event.pageY - $line.parent().offset().top;
                this.display_client_details('show',partner,y);
                this.new_client = partner;
                this.toggle_save_button();
            }
        },
        partner_icon_url: function(id){
            return '/web/image?model=res.partner&id='+id+'&field=image_small';
        },

        // ui handle for the 'edit selected customer' action
        edit_client_details: function(partner) {
            this.display_client_details('edit',partner);
        },

        // ui handle for the 'cancel customer edit changes' action
        undo_client_details: function(partner) {
            if (!partner.id) {
                this.display_client_details('hide');
            } else {
                this.display_client_details('show',partner);
            }
        },

        // what happens when we save the changes on the client edit form -> we fetch the fields, sanitize them,
        // send them to the backend for update, and call saved_client_details() when the server tells us the
        // save was successfull.
        save_client_details: function(partner) {
            var self = this;

            var fields = {};
            this.$el.find('.client-details-contents .detail').each(function(idx,el){
                fields[el.name] = el.value || false;
            });

            if (!fields.name) {
                this.gui.show_popup('error',_t('A Customer Name Is Required'));
                return;
            }

            if (this.uploaded_picture) {
                fields.image = this.uploaded_picture;
            }

            fields.id           = partner.id || false;
            fields.country_id   = fields.country_id || false;

            var contents = this.$el.find(".client-details-contents");
            contents.off("click", ".button.save");

            new Model('res.partner').call('create_from_ui',[fields]).then(function(partner_id){
                self.saved_client_details(partner_id);
            },function(err,event){
                event.preventDefault();
                var error_body = _t('Your Internet connection is probably down.');
                if (err.data) {
                    var except = err.data;
                    error_body = except.arguments && except.arguments[0] || except.message || error_body;
                }
                self.gui.show_popup('error',{
                    'title': _t('Error: Could not Save Changes'),
                    'body': error_body,
                });
                contents.on('click','.button.save',function(){ self.save_client_details(partner); });
            });
        },

        // what happens when we've just pushed modifications for a partner of id partner_id
        saved_client_details: function(partner_id){
            var self = this;
            this.reload_partners().then(function(){
                var partner = self.pos.db.get_partner_by_id(partner_id);
                if (partner) {
                    self.new_client = partner;
                    self.toggle_save_button();
                    self.display_client_details('show',partner);
                } else {
                    // should never happen, because create_from_ui must return the id of the partner it
                    // has created, and reload_partner() must have loaded the newly created partner.
                    self.display_client_details('hide');
                }
            }).always(function(){
                $(".client-details-contents").on('click','.button.save',function(){ self.save_client_details(partner); });
            });
        },

        // resizes an image, keeping the aspect ratio intact,
        // the resize is useful to avoid sending 12Mpixels jpegs
        // over a wireless connection.
        resize_image_to_dataurl: function(img, maxwidth, maxheight, callback){
            img.onload = function(){
                var canvas = document.createElement('canvas');
                var ctx    = canvas.getContext('2d');
                var ratio  = 1;

                if (img.width > maxwidth) {
                    ratio = maxwidth / img.width;
                }
                if (img.height * ratio > maxheight) {
                    ratio = maxheight / img.height;
                }
                var width  = Math.floor(img.width * ratio);
                var height = Math.floor(img.height * ratio);

                canvas.width  = width;
                canvas.height = height;
                ctx.drawImage(img,0,0,width,height);

                var dataurl = canvas.toDataURL();
                callback(dataurl);
            };
        },

        // Loads and resizes a File that contains an image.
        // callback gets a dataurl in case of success.
        load_image_file: function(file, callback){
            var self = this;
            if (!file.type.match(/image.*/)) {
                this.gui.show_popup('error',{
                    title: _t('Unsupported File Format'),
                    body:  _t('Only web-compatible Image formats such as .png or .jpeg are supported'),
                });
                return;
            }

            var reader = new FileReader();
            reader.onload = function(event){
                var dataurl = event.target.result;
                var img     = new Image();
                img.src = dataurl;
                self.resize_image_to_dataurl(img,800,600,callback);
            };
            reader.onerror = function(){
                self.gui.show_popup('error',{
                    title :_t('Could Not Read Image'),
                    body  :_t('The provided file could not be read due to an unknown error'),
                });
            };
            reader.readAsDataURL(file);
        },

        // This fetches partner changes on the server, and in case of changes,
        // rerenders the affected views
        reload_partners: function(){
            var self = this;
            return true;
            //case create customer
            /*return this.pos.load_new_partners().then(function(){
                // partners may have changed in the backend
                self.partner_cache = new screens.DomCache();

                //self.render_list(self.pos.db.get_partners_sorted(1000));
                self.render_list([]);

                // update the currently assigned client if it has been changed in db.
                var curr_client = self.pos.get_order().get_client();
                if (curr_client) {
                    self.pos.get_order().set_client(self.pos.db.get_partner_by_id(curr_client.id));
                }
            });*/
        },

        // Shows,hides or edit the customer details box :
        // visibility: 'show', 'hide' or 'edit'
        // partner:    the partner object to show or edit
        // clickpos:   the height of the click on the list (in pixel), used
        //             to maintain consistent scroll.
        display_client_details: function(visibility,partner,clickpos){
            var self = this;
            var searchbox = this.$el.find('.searchbox input');
            var contents = this.$el.find('.client-details-contents');
            var parent   = this.$el.find('.client-list').parent();
            var scroll   = parent.scrollTop();
            var height   = contents.height();

            contents.off('click','.button.edit');
            contents.off('click','.button.save');
            contents.off('click','.button.undo');
            contents.on('click','.button.edit',function(){ self.edit_client_details(partner); });
            contents.on('click','.button.save',function(){ self.save_client_details(partner); });
            contents.on('click','.button.undo',function(){ self.undo_client_details(partner); });
            this.editing_client = false;
            this.uploaded_picture = null;

            if(visibility === 'show'){
                contents.empty();
                contents.append($(QWeb.render('ClientDetailsAPI',{widget:this,partner:partner})));

                var new_height   = contents.height();

                if(!this.details_visible){
                    // resize client list to take into account client details
                    parent.height('-=' + new_height);

                    if(clickpos < scroll + new_height + 20 ){
                        parent.scrollTop( clickpos - 20 );
                    }else{
                        parent.scrollTop(parent.scrollTop() + new_height);
                    }
                }else{
                    parent.scrollTop(parent.scrollTop() - height + new_height);
                }

                this.details_visible = true;
                this.toggle_save_button();
            }
            else if (visibility === 'hide'){
                contents.empty();
                parent.height('100%');
                if( height > scroll ){
                    contents.css({height:height+'px'});
                    contents.animate({height:0},400,function(){
                        contents.css({height:''});
                    });
                }else{
                    parent.scrollTop( parent.scrollTop() - height);
                }
                this.details_visible = false;
                this.toggle_save_button();
            }
            /*else if (visibility === 'edit') {
                // Connect the keyboard to the edited field
                if (this.pos.config.iface_vkeyboard && this.chrome.widget.keyboard) {
                    contents.off('click', '.detail');
                    searchbox.off('click');
                    contents.on('click', '.detail', function(ev){
                        self.chrome.widget.keyboard.connect(ev.target);
                        self.chrome.widget.keyboard.show();
                    });
                    searchbox.on('click', function() {
                        self.chrome.widget.keyboard.connect($(this));
                    });
                }

                this.editing_client = true;
                contents.empty();
                contents.append($(QWeb.render('ClientDetailsEditAPI',{widget:this,partner:partner})));
                this.toggle_save_button();

                // Browsers attempt to scroll invisible input elements
                // into view (eg. when hidden behind keyboard). They don't
                // seem to take into account that some elements are not
                // scrollable.
                contents.find('input').blur(function() {
                    setTimeout(function() {
                        self.$el.find('.window').scrollTop(0);
                    }, 0);
                });

                contents.find('.image-uploader').on('change',function(event){
                    self.load_image_file(event.target.files[0],function(res){
                        if (res) {
                            contents.find('.client-picture img, .client-picture .fa').remove();
                            contents.find('.client-picture').append("<img src='"+res+"'>");
                            contents.find('.detail.picture').remove();
                            self.uploaded_picture = res;
                        }
                    });
                });
            }*/
        },
        close: function(){
            this._super();
            if (this.pos.config.iface_vkeyboard && this.chrome.widget.keyboard) {
                this.chrome.widget.keyboard.hide();
            }
        },
    });
    gui.define_screen({name:'clientlistapi', widget: ClientListAPIScreenWidget});

    CardListScreenWidget.include({
        get_request_header: function(date){
            var header = this._super(date);

            var self = this;
            var now = moment(date);

            header.SourceTransID = [
                'OFM',
                self.pos.branch.branch_code,
                self.pos.get_order().uid,
                now.format('DDMMYYYY_HH:mm:ss:SSS')
            ].join('_');

            return header;
        },
    });

    ClientListAPIScreenWidget.include({
        render_list: function(partners){
            var filtered_partners = _.filter(partners, function(partner){
                if (partner.company_id[0] === posmodel.company.id){
                    return true;
                }
            });
            this._super(filtered_partners);
        },
    });


    return {
        SaleOrderListScreenWidget: SaleOrderListScreenWidget,
        SaleOrderWidget: SaleOrderWidget,
        SaleOrderFormScreenWidget: SaleOrderFormScreenWidget,
        ClientListAPIScreenWidget: ClientListAPIScreenWidget,
    }
});