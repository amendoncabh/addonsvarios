odoo.define('pos_sale_order.model', function (require) {
    "use strict";
    var core = require('web.core');
    var models = require('point_of_sale.models');
    var Model = require('web.DataModel');
    var PosDB = require('point_of_sale.DB');
    var session = require('web.session');
    var formats = require('web.formats');
    var gui = require('point_of_sale.gui').Gui;
    var _t = core._t;


if(odoo.session_info && 'sale_type' in odoo.session_info){

    models.load_fields('product.product', ['is_delivery_fee_ofm', 'delivery_fee_ofm', 'prod_status']);

    models.load_models([{
        model:  'sale.order',
        fields: ['name', 'quotation_no', 'partner_id', 'date_order', 'amount_total', 'state'],
        limit: 100,
        domain: function(self){
        return [
            ['type_sale_ofm', '=', (odoo.session_info.sale_type == 'dropship')],
            ['branch_id','=', self.branch.id],
            ['state','in', ['draft', 'sent']]
            ];
        },
        loaded: function(self, parameters){
            parameters && parameters.forEach(function(order){
                self.db.order_by_id[order.id] = order;
            });
        },
    }, {
        model:  'ir.config_parameter',
        fields: ['key','value'],
        domain: function(self){ return [['key', 'in', [
            'so_quotation_expire_amount_day',
            'so_delivery_fee_special'
        ]]]; },
        loaded: function(self, parameters){
            parameters.forEach(function(parameter){
                self[parameter.key] = parseInt(parameter.value);
            });
        },
    }, {
        model:  'ir.config_parameter',
        fields: ['key','value'],
        domain: function(self){ return [['key', 'in', [
            'pos_sale_order_discount_see',
            'pos_sale_order_discount_see_dropship',
        ]]]; },
        loaded: function(self, parameters){
            parameters.forEach(function(parameter){
                if(parameter.value == 'True')
                    self[parameter.key] = true;
                else
                    self[parameter.key] = false;
            });
        },
    }, {
        label: 'menu_sale_quotations',
        loaded: function(self){
            return session.rpc('/web/new_tab_api/', {
                model_name: 'sale.order',
                menu_id: 'sale.menu_sale_quotations',
                action_id: 'sale.action_quotations',
            }).then(function(result){
                self.menu_sale_quotations = result;
            });
        },
    }, {
        label: 'menu_ofm_quotations',
        loaded: function(self){
            return session.rpc('/web/new_tab_api/', {
                model_name: 'sale.order',
                menu_id: 'ofm_so_ext.menu_ofm_quotations',
                action_id: 'ofm_so_ext.dropship_quotations_action',
            }).then(function(result){
                self.menu_ofm_quotations = result;
            });
        },
    }, {
        label: 'menu_sale_order',
        loaded: function(self){
            return session.rpc('/web/new_tab_api/', {
                model_name: 'sale.order',
                menu_id: 'sale.menu_sale_order',
                action_id: 'sale.action_orders',
            }).then(function(result){
                self.menu_sale_order = result;
            });
        },
    }, {
        label: 'menu_ofm_sales_order',
        loaded: function(self){
            return session.rpc('/web/new_tab_api/', {
                model_name: 'sale.order',
                menu_id: 'ofm_so_ext.menu_ofm_sales_order',
                action_id: 'ofm_so_ext.dropship_sales_order_action',
            }).then(function(result){
                self.menu_ofm_sales_order = result;
            });
        },
    }, {
        label: 'menu_account_refund',
        loaded: function(self){
            return session.rpc('/web/new_tab_api/', {
                model_name: 'account.invoice',
                menu_id: 'account.menu_finance',
                action_id: 'account.action_invoice_tree1',
            }).then(function(result){
                self.menu_account_refund = result;
            });
        },
    }, {
        label: 'menu_customer_payments',
        loaded: function(self){
            return session.rpc('/web/new_tab_api/', {
                model_name: 'account.payment',
                menu_id: 'ofm_custom_tr_account_v10.menu_action_account_payments_customer',
                action_id: 'ofm_custom_tr_account_v10.action_account_payments_customer',
            }).then(function(result){
                self.menu_customer_payments = result;
            });
        },
    }, {
        label: 'timeout_save_server',
        loaded: function(self, parameters){
            return new Model('pos.config').call('get_time_save_to_server').then(function(result){
                self.timeout_save_server = result;
            });
        },
    }]);

    if (odoo.session_info.sale_type == 'dropship') {
        models.load_models([{
            model:  'ir.config_parameter',
            fields: ['key','value'],
            domain: function(self){ return [ ['key','in', ['prs_product_status']] ]; },
            limit: 1,
            loaded: function(self, parameters){
                parameters.forEach(function(parameter){
                    if(parameter.key == 'prs_product_status'){
                        var values = ['free'];
                        parameter.value.split(',').forEach(function(value){
                            values.push(value.toLowerCase());
                        });
                        self.db.prs_product_status = values;
                        self.db.prs_product_status_ol = parameter.value.split(',');
                    }
                });
            },
        }], {
            'before': 'product.product'
        });

        models.load_models([{
            model:  'product.price.dropship',
            fields: ['product_product_id'],
            domain: [],
            loaded: function(self, products){
                //console.log('products', products)
                //self.db.template_product_ids = [];
                var template_product_ids = [];
                products.forEach(function(product){
                    //if(product.is_dropship_active)
                    template_product_ids.push(product.product_product_id);
                });

                if(self.config.promotion_discount_product_id){
                    template_product_ids.push(self.config.promotion_discount_product_id[0]);
                }
                if(self.config.vip_discount_product_id){
                     template_product_ids.push(self.config.vip_discount_product_id[0]);
                }

                if(self.db.template_product_ids instanceof Array)
                    self.db.template_product_ids = self.template_product_ids = _.union(self.db.template_product_ids, template_product_ids);
                else
                    self.db.template_product_ids = self.template_product_ids = template_product_ids;
            },
        }], {
            'replace': 'pos.product.template.line'
        });

        PosDB.include({
            add_products: function (products, filter_template=false) {
                var self = this;
                products = products.filter(function(product){
                    if(product.prod_status && product.prod_status.length){
                        return self.prs_product_status.includes(product.prod_status.toLowerCase());
                    }
                    else{
                        return true;
                    }
                });
                this._super(products, filter_template);
            },
        });
    }

    var posmodel_super = models.PosModel.prototype;
    models.PosModel = models.PosModel.extend({
        _save_to_server: function (orders, options) {
            if (!orders || !orders.length) {
                var result = $.Deferred();
                result.resolve([]);
                return result;
            }

            options = options || {};

            var self = this;
            const timeout_config = typeof self.timeout_save_server === 'number' ? self.timeout_save_server : 7500;
            var timeout = typeof options.timeout === 'number' ? options.timeout : timeout_config * orders.length;

            // Keep the order ids that are about to be sent to the
            // backend. In between create_from_ui and the success callback
            // new orders may have been added to it.
            var order_ids_to_sync = _.pluck(orders, 'id');

            // remove all order in cache
            _.each(order_ids_to_sync, function (order_id) {
                self.db.remove_order(order_id);
            });

            // we try to send the order. shadow prevents a spinner if it takes too long. (unless we are sending an invoice,
            // then we want to notify the user that we are waiting on something )
            var saleOrderModel = new Model('sale.order');
            return saleOrderModel.call('create_from_ui',
                [_.map(orders, function (order) {
                    order.to_invoice = options.to_invoice || false;
                    return order;
                })],
                undefined,
                {
                    shadow: !options.to_invoice,
                    timeout: timeout
                }
            ).then(function (server_ids) {
                self.set('failed',false);
                return server_ids;
            }).fail(function (error, event){
                if(error.code === 200 ){    // Business Logic Error, not a connection problem
                    //if warning do not need to display traceback!!
                    if (error.data.exception_type == 'warning') {
                        delete error.data.debug;
                    }

                    // Hide error if already shown before ...
                    if ((!self.get('failed') || options.show_error) && !options.to_invoice) {
                        self.gui.show_popup('error-traceback',{
                            'title': error.data.message,
                            'body':  error.data.debug
                        });
                    }
                    self.set('failed',error)
                }
                // prevent an error popup creation by the rpc failure
                // we want the failure to be silent as we send the orders in the background
                event.preventDefault();
                console.error('Failed to send orders:', orders);
            });
        },
        load_server_data: function () {
            var self = this;
            if(odoo.session_info.sale_session_id){
                self.session_info = odoo.session_info;
                var pos_session = -1, pos_config = -1, pos_product_template = -1, pos_promotion = -1
                    ,res_partner = -1;
                self.models.forEach(function(model, index){
                    if(pos_session === -1 && model.model === 'pos.session')
                        pos_session = index;
                    else if(pos_config === -1 && model.model === 'pos.config')
                        pos_config = index;
                    else if(pos_promotion === -1 && model.model === 'pos.promotion')
                        pos_promotion = index;
                    else if(res_partner === -1 && model.model === 'res.partner')
                        res_partner = index;
                });

                if(pos_promotion !== -1){
                    var promotion_super_domain = self.models[pos_promotion].domain;
                    var domain = function(self){
                        var promotion_domain = promotion_super_domain(self);

                        var domain_idx = promotion_domain.findIndex(function(arr){
                            return arr.find(item => item == 'is_channel_pos');
                        });
                        var filter_channel = 'is_channel_instore';
                        if(odoo.session_info.sale_type == 'dropship')
                            filter_channel = 'is_channel_dropship'

                        if(domain_idx >= 0){
                            promotion_domain[domain_idx] = [filter_channel, '=', 'True'];
                        }
                        else{
                            promotion_domain.push([filter_channel, '=', 'True'])
                        }
                        return promotion_domain;
                    }
                    self.models[pos_promotion].domain = domain;
                }

                if(pos_session !== -1)
                    self.models[pos_session] = {
                        model:  'sale.session',
                        fields: [],
                        domain: function(self){ return [['id','=', odoo.session_info.sale_session_id]]; },
                        loaded: function(self,pos_sessions){
                            self.pos_session = pos_sessions[0];
                            self.pos_session.start_at = self.pos_session.write_date;
                        },
                    };

                if(pos_config !== -1)
                    self.models[pos_config] = {
                        model: 'pos.config',
                        fields: [],
                        domain: function(self){ return [['id','=', self.pos_session.config_id[0]]]; },
                        loaded: function(self,configs){
                            self.config = configs[0];
                            self.config.use_proxy = self.config.iface_payment_terminal ||
                                                    self.config.iface_electronic_scale ||
                                                    self.config.iface_print_via_proxy  ||
                                                    self.config.iface_scan_via_proxy   ||
                                                    self.config.iface_cashdrawer;

                            if (self.config.company_id[0] !== self.user.company_id[0]) {
                                throw new Error(_t("Error: The Point of Sale User must belong to the same company as the Point of Sale. You are probably trying to load the point of sale as an administrator in a multi-company setup, with the administrator account set to the wrong company."));
                            }
                            //replace so uuid to pos uuid
                            self.config.uuid = self.config.so_uuid;

                            self.db.set_uuid(self.config.uuid);
                            self.cashier = self.get_cashier();
                            // We need to do it here, since only then the local storage has the correct uuid
                            self.db.save('pos_session_id', self.pos_session.id);

                            var orders = self.db.get_orders();
                            for (var i = 0; i < orders.length; i++) {
                                self.pos_session.sequence_number = Math.max(self.pos_session.sequence_number, orders[i].data.sequence_number+1);
                            }
                        },
                    };


                if(res_partner !== -1){
                    self.models.splice(res_partner, 1);
                }
            }
            return posmodel_super.load_server_data.call(this);
        },
        set_sale_order_from_db: function(id){
            var self = this;
            if(!(id && id in self.db.order_by_id))
                return false;

            var order = self.db.order_by_id[id];

            var order_obj = self.get_order();

            order_obj.amount_delivery_fee_by_order = order.amount_delivery_fee_by_order;
            order_obj.amount_delivery_fee_special = order.amount_delivery_fee_special;

            var remove_orderlines = [];
            order_obj.get_orderlines().forEach(function(line){
                remove_orderlines.push(line);
            });

            remove_orderlines.forEach(function(line){
                order_obj.remove_orderline(line);
            });

            order.lines = [];
            order.statement_ids = [];
            if(order.pos_sale_reference && order.pos_sale_reference.length){
                order_obj.uid = order.pos_sale_reference.split(' ')[1];
            }
            order_obj.order_id = order.id;
            order_obj.quotation_no = order.quotation_no;
            order_obj.so_name = order.name;

            order_obj.pos_offline = order.pos_offline;
            order_obj.t1c_set = order.t1c_set;

            if(order.membercard){
                order_obj.membercard = order.membercard;
            }
            else{
                order_obj.membercard = {
                    'the_one_card_no': order.the_one_card_no,
                    'member_name': 'N/A',
                    'card_type': 'N/A',
                    'customer_group_segment': 'N/A',
                    'phone': order.phone_number,
                    'company': 'N/A',
                    'status': 'N/A',
                    'tier': 'N/A',
                    'cg_staff': 'N/A',
                    'balance_points': 'N/A',
                    'redeem_rights': 'N/A',
                    'segment': 'N/A',
                    'staff': 'N/A',
                    'expire_this_year': 'N/A',
                };
            }

            if(order_obj.pos_offline === false){
                order_obj.membercard.expire_this_year = order.points_expiry_this_year;
                order_obj.membercard.balance_points = order.points_balance;
                order_obj.membercard.member_name = order.member_name;
            }

            order_obj.validation_date = order.date_order;
            order_obj.formatted_validation_date = formats.format_value(
                order_obj.validation_date , {type: 'datetime'});

            order_obj.expiration_date = order.validity_date;
            order_obj.formatted_expiration_date = formats.format_value(
                order_obj.expiration_date, {type: 'datetime'});


            // prepare customer
            var customer = order.partner_id[0]
            customer.full_address = self.db.gen_partner_full_address(customer);

            if(order.partner_invoice_id && !_.isNumber(order.partner_invoice_id[0])
            && order.partner_invoice_id[0].id != customer.id){
                customer.invoice_address_id = order.partner_invoice_id[0].id;
                customer.full_invoice_address = self.db.gen_partner_full_address(order.partner_invoice_id[0]);
            }

            if(order.partner_shipping_id && !_.isNumber(order.partner_shipping_id[0])
            && order.partner_shipping_id[0].id != customer.id){
                customer.delivery_address_id = order.partner_shipping_id[0].id;
                customer.full_delivery_address = self.db.gen_partner_full_address(order.partner_shipping_id[0]);
            }

            if(order.contact_id && !_.isNumber(order.contact_id[0])
            && order.contact_id[0].id != customer.id){
                customer.contact_address_id = order.contact_id[0].id;
            }
            self.db.partner_by_id[customer.id] = customer;
            order.partner_id = customer.id;


            var orderlines_obj = [];
            var amount_delivery_fee_by_order = 0;
            var amount_delivery_fee_special = 0;
            var amount_discount_by_order = 0;
            // create order lines
            order.order_line.forEach(function(orderline){
                if(orderline.is_type_discount_f_see)
                    amount_discount_by_order += Math.abs(orderline.price_unit);

                if(orderline.is_type_delivery_by_order){
                    amount_delivery_fee_by_order += Math.abs(orderline.price_unit);
                }
                else if(orderline.is_type_delivery_special){
                    amount_delivery_fee_special += Math.abs(orderline.price_unit);
                }
                else{
                    orderline.taxes_id = orderline.tax_id;
                    orderline.product_id = orderline.product_id[0];
                    orderline.pack_lot_ids = orderline.pack_lot_ids || [];
                    orderline.qty = orderline.product_uom_qty;

                    orderline.promotion_id = (orderline.promotion_id instanceof Array) ? orderline.promotion_id[0] : undefined;
                    orderline.promotion_condition_id = (orderline.promotion_condition_id instanceof Array)? orderline.promotion_condition_id[0] : undefined;
                    orderline.free_product_id = (orderline.free_product_id instanceof Array)? orderline.free_product_id[0] : undefined;
                    if(orderline.is_coupon){
                        orderline.is_danger = false;
                    }
                    var orderline_obj = new models.Orderline({},{order:order_obj, pos:self, json: orderline});
                    order_obj.orderlines.add(orderline_obj);
                }
            });
            if(order_obj.amount_discount_by_order != amount_discount_by_order){
                order_obj.amount_discount_by_order = amount_discount_by_order;
                order_obj.amount_discount_by_order_text = amount_discount_by_order+'';
            }

            if(order_obj.amount_delivery_fee_by_order != amount_delivery_fee_by_order)
                order_obj.amount_delivery_fee_by_order = amount_delivery_fee_by_order;

            if(order_obj.amount_delivery_fee_special != amount_delivery_fee_special)
                order_obj.amount_delivery_fee_special = amount_delivery_fee_special;

            order_obj.is_calculated_promotion = order_obj.is_applied_promotion();

            order_obj.set_client(customer);

            // set back for display in line
            order.partner_id = [customer.id, customer.name];
        },
    });

    var _super_order = models.Order.prototype;
    models.Order = models.Order.extend({
        initialize: function (attributes, options) {
            //_super_order
            _super_order.initialize.call(this, attributes, options);
            this.initialize_validation_date();
            this.temporary = true;
            this.type_sale_ofm = (odoo.session_info.sale_type == 'dropship');
        },
        initialize_validation_date: function(){
            _super_order.initialize_validation_date.call(this);
            this.expiration_date = new Date(this.validation_date.getTime() + 86400000 * this.pos.so_quotation_expire_amount_day);
            this.formatted_expiration_date = formats.format_value(
                this.expiration_date, {type: 'datetime'});
        },
        init_from_JSON: function (json) {
            this.formatted_validation_date = formats.format_value(
                this.validation_date , {type: 'datetime'});
            this.expiration_date = json.validity_date;
            this.formatted_expiration_date = formats.format_value(
                this.expiration_date, {type: 'datetime'});
            this.type_sale_ofm = json.type_sale_ofm;
            this.note = json.note;
            this.amount_delivery_fee_special = json.amount_delivery_fee_special;
            this.amount_delivery_fee_by_order = json.amount_delivery_fee_by_order;
            this.amount_discount_by_order = json.amount_discount_by_order;

            if(json.order_id){
                this.order_id = json.order_id;
            }

            _super_order.init_from_JSON.call(this, json);
        },
        export_as_JSON: function () {
            var json = _super_order.export_as_JSON.call(this);
            json.name = 'Sale ' + this.uid;
            json.validity_date = this.expiration_date;
            json.type_sale_ofm = this.type_sale_ofm;
            json.note = this.note;
            json.amount_delivery_fee_special = this.amount_delivery_fee_special;
            json.amount_delivery_fee_by_order = this.amount_delivery_fee_by_order;
            json.amount_discount_by_order = this.amount_discount_by_order;
            json.discount_approval_manager = this.discount_approval_manager;
            json.discount_approval_time = this.discount_approval_time;
            json.order_id = this.order_id;

            var client = this.get_client()
            if(client){
                json.partner_invoice_id  = client.invoice_address_id || client.id;
                json.partner_shipping_id = client.delivery_address_id || client.id;
                json.contact_id = client.contact_address_id || client.id;
                if(client.property_payment_term_id){
                    json.payment_term_id = client.property_payment_term_id[0];
                }
            }
            return json;
        },
        add_product: function (product, options) {
            var screen_name = this.pos.gui.get_current_screen();
            if (screen_name == 'sale_order_form' && !this.doing_promotion && this.is_calculated_promotion) {
                document.getElementsByClassName("discount_see").discount_see.value = '';
                this.amount_discount_text = '';
                this.reverse_promotions();
            }
            if(product.prod_status && product.prod_status.toLowerCase() == 'free'
            && !this.doing_promotion){
                return;
            }
            _super_order.add_product.call(this, product, options);
            this.calculate_shipping_fee_by_order();
        },
        reverse_promotions: function(){
            var order = this;
            _super_order.reverse_promotions.call(this);

            order.amount_discount_by_order = 0;
        },
        check_cash_limit: function () {
            return true;
        },
        possible_promotion: function(origin_lines, targets, time=1, exclude_tiers=false){
            var self = this;
            var product_ids = undefined;
            if(odoo.session_info && 'sale_type' in odoo.session_info && (odoo.session_info.sale_type == 'dropship' || odoo.session_info.sale_type == 'instore')){
                if(!targets.reward_target.is_discount){
                    targets.reward_target.skip_reward = true;
                    var product_by_id = self.pos.db.product_by_id;
                    product_ids = [];

                    if(targets.reward_target.reward_mapping_product_qty_ids){
                        targets.reward_target.reward_mapping_product_qty_ids.forEach(function(product_qty){
                            product_ids.push({
                                product_id: product_qty.product_id_int,
                                quantity: product_qty.qty * time,
                                force_add: true,
                            });
                        });
                    }
                    else{
                        if(targets.is_free_as_same_pid){
                            targets.target_amount_same_pid = targets.condition_target.amount;
                        }
                        else{
                            var min_price_product_id = _.min(
                                _.intersection(targets.reward_target.product_ids, self.pos.db.template_product_ids),
                                function(product_id){
                                    if(product_by_id[product_id])
                                        return  product_by_id[product_id].price;
                                    return Infinity;
                                }
                            );
                            if(min_price_product_id !== Infinity)
                                product_ids.push({
                                    product_id: min_price_product_id,
                                    quantity: targets.reward_target.amount * time,
                                    force_add: true,
                                });
                        }
                    }
                }
            }
            var result =  _super_order.possible_promotion.call(self, origin_lines, targets, time, exclude_tiers);
            if(odoo.session_info && 'sale_type' in odoo.session_info && (odoo.session_info.sale_type == 'dropship' || odoo.session_info.sale_type == 'instore')){
                if(result.success && product_ids){
                    if(targets.is_free_as_same_pid){
                        result.product_ids.forEach(function(item){
                            item.force_add = true;
                        });
                    }
                    else{
                        result.product_ids = product_ids;
                    }
                }
            }
            return result;
        },
        add_discount_f_see: function(){
            if(this.amount_discount_text && this.amount_discount_text.length){
                this.doing_promotion = true;
                if(this.amount_discount_by_order){
                    this.reverse_promotions();
                }

                var promotion_name = 'ส่วนลดพิเศษ '+ this.amount_discount_text;
                var discount_amount = this.amount_discount_text.split('%');
                var is_percent = false;
                if(discount_amount.length > 1){
                    is_percent = true;
                }
                else
                    promotion_name += 'บาท';

                discount_amount = parseFloat(discount_amount[0]);

                var focus_lines = this.get_orderlines().filter((line)=> !line.promotion);

                this.add_discount_with_prorate(focus_lines, discount_amount, is_percent, 1, {
                    promotion_name: promotion_name,
                    is_type_discount_f_see : true,
                    second_prorate: true,
                });
                this.is_calculated_promotion  = true;
                var discount_f_see = this.get_orderlines().find((line)=>line.is_type_discount_f_see);
                if(discount_f_see)
                    this.amount_discount_by_order = Math.abs(discount_f_see.price);

                this.doing_promotion = false;
            }
            else{
                this.doing_promotion = true;
                if(this.amount_discount_by_order){
                    this.reverse_promotions();
                }
                this.doing_promotion = false;
            }
        },
        apply_promotions: function(){
            var result = _super_order.apply_promotions.call(this);
            this.add_discount_f_see();
            return result;
        },
        calculate_shipping_fee_by_order: function(){
            if(odoo.session_info.sale_type == 'dropship'){
                var order = this;
                order.amount_delivery_fee_by_order = 0;
                order.amount_delivery_fee_special = 0;
                if(order.get_total_with_tax() < 499){
                    order.amount_delivery_fee_by_order = this.pos.so_delivery_fee_special;
                }
                this.trigger('change');
            }
        },
    });

    var _super_orderline = models.Orderline;
    models.Orderline = models.Orderline.extend({
        init_from_JSON: function(json){
            _super_orderline.prototype.init_from_JSON.call(this, json);
            this.is_danger = json.is_danger;
            this.is_coupon = json.is_coupon;
            this.product_qty_available = json.product_qty_available;
            if(json.product_status_odoo && json.product_status_odoo.length)
                this.product_status_odoo = json.product_status_odoo;
            if(json.product_status_ofm && json.product_status_ofm.length)
                this.product_status_ofm = json.product_status_ofm;

            this.is_type_discount_f_see = json.is_type_discount_f_see;
        },
        export_as_JSON: function (){
            var json = _super_orderline.prototype.export_as_JSON.call(this);
            json.product_uom_qty = this.quantity;
            if(this.product_status_odoo && this.product_status_odoo.length)
                json.product_status_odoo = this.product_status_odoo;
            else
                json.product_status_odoo = this.product.prod_status;

            json.is_type_discount_f_see = this.is_type_discount_f_see;

            return json;
        },
    });

    gui.include({
        _close: function() {
            var self = this;
            if('sale_type' in odoo.session_info){
                this.chrome.loading_show();
                this.chrome.loading_message(_t('Closing ...'));

                this.pos.push_order().then(function(){
                    var url = "/web#action=pos_sale_order.action_pos_config_kanban_so";
                    window.location = session.debug ? $.param.querystring(url, {debug: session.debug}) : url;
                });
            }
            else{
                this._super();
            }
        },
    });
}

});
