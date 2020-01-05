
odoo.define('pos_customize.custom', function (require) {
    "use strict";

    var chrome = require('point_of_sale.chrome');
    var gui = require('point_of_sale.gui');
    var models = require('point_of_sale.models');
    var basewidget = require('point_of_sale.BaseWidget');

    var PosDB = require('point_of_sale.DB');
    var Model = require('web.DataModel');
    var screens = require('point_of_sale.screens');
    var core = require('web.core');
    var utils = require('web.utils');
    var round_pr = utils.round_precision;
    var formats = require('web.formats');
    var time = require('web.time');
    var round_di = utils.round_decimals;


    var QWeb = core.qweb;
    var _t = core._t;
    var count_pos_tab = {};

    var exports = {};


    var tmp_widgets = chrome.Chrome.prototype.widgets;
    var close_button_i = (tmp_widgets.length);
    for (var i = 0; i < tmp_widgets.length; i++) {
        if (tmp_widgets[i].name === 'close_button') {
            close_button_i = i;
            break;
        }
    }

    gui.Gui.include({
        ask_password: function(password) {
            var self = this;
            var ret = new $.Deferred();
            if (password) {
                this.show_popup('password',{
                    'title': _t('Password ?'),
                    confirm: function(pw) {
                        if (pw !== password) {
                            self.show_popup('error',_t('Incorrect Password'));
                            ret.reject();
                        } else {
                            ret.resolve();
                        }
                    },
                    cancel: function(){
                        ret.reject();
                    },
                });
            } else {
                ret.resolve();
            }
            return ret;
        },
    });

    tmp_widgets[close_button_i] = {
        'name': 'close_button',
        'widget': chrome.HeaderButtonWidget,
        'append': '.pos-rightheader',
        'args': {
            label: _t('Close'),
            action: function () {
                var self = this;
                if (!this.confirmed) {
                    // check order here
                    var count_orderline = 0;
                    $.each(this.pos.get_order_list(), function (i, e) {
                        count_orderline += e.orderlines.length;
                    });
                    if (count_orderline > 0) {
                        this.gui.show_popup('alert', {
                            'title': 'Alert',
                            'body': 'ยังมีบางรายการค้างอยู่กรุณาตรวจสอบ',
                        });
                    } else {
                        this.$el.addClass('confirm');
                        this.$el.text(_t('Confirm'));
                        this.confirmed = setTimeout(function () {
                            self.$el.removeClass('confirm');
                            self.$el.text(_t('Close'));
                            self.confirmed = false;
                        }, 2000);
                    }
                } else {
                    clearTimeout(this.confirmed);
                    this.gui.close();
                }
            },
        }
    };

    chrome.Chrome.include({
        'widgets': tmp_widgets
    });

    _.recursiveDeepCopy = function(o) {
        var newO, i;

        if (typeof o !== 'object') {
            return o;
        }
        if (!o) {
            return o;
        }

        if ('[object Array]' === Object.prototype.toString.apply(o)) {
            newO = [];
            for (i = 0; i < o.length; i += 1) {
                newO[i] = _.recursiveDeepCopy(o[i]);
            }
            return newO;
        }

        newO = {};
        for (i in o) {
            if (o.hasOwnProperty(i)) {
                newO[i] = _.recursiveDeepCopy(o[i]);
            }
        }
        return newO;
    }

//    chrome.UsernameWidget.include({
//        click_username: function(){
//
//        },
//    })

    //
    models.load_fields('product.product', ['pricelist_type', 'pricelist_percent_price', 'hide_in_pos_product_list', 'exempt_pos_calculate', 'categ_id', 'all_categories', 'is_hold_sale', 'is_best_deal_promotion']);

    var pmodels = models.PosModel.prototype.models;

    models.order_model = function (model_name, fields) {
        var index = false;
        for (var i = 0; i < pmodels.length; i++) {
            if (pmodels[i].model === model_name ||
                    pmodels[i].label === model_name) {
                index = i;
            }
        }

        if (index !== false) {
            pmodels[index].order = fields;
        }
    };


    var res_partner_model = pmodels.find(model=>(model.model && model.model == 'res.partner'));
    if(res_partner_model){
        res_partner_model.domain.push(['parent_id', '=', false]);
    }

    //res.partner
    models.load_fields('res.partner', ['company_type', 'shop_id']);

    models.load_models([
        {
            model: 'res.country.state',
            fields: ["name", "code", "country_id"],
            loaded: function (self, states) {
                self.states = states;
            },
        },{
        model: 'pos.config',
        fields: ['rcpt_no_abb_round', 'rcpt_no_abb_latest'],
        domain: function(self){ return [['id','=', self.pos_session.config_id[0]]]; },
        loaded: function(self,configs){
            if(configs.length == 1){
                self.config.rcpt_no_abb_round = configs[0].rcpt_no_abb_round;
                self.config.rcpt_no_abb_latest = configs[0].rcpt_no_abb_latest;

                var rcpt_no_abb_round_cache = self.db.load('rcpt_no_abb_round') || 0;
                var rcpt_no_abb_latest_cache = self.db.load('rcpt_no_abb_latest') || 1;

                var flag_update = false;
                if(rcpt_no_abb_round_cache > self.config.rcpt_no_abb_round){
                    self.config.rcpt_no_abb_round = rcpt_no_abb_round_cache
                    self.config.rcpt_no_abb_latest = rcpt_no_abb_latest_cache
                    flag_update = true;
                }
                else{
                    if(rcpt_no_abb_latest_cache > self.config.rcpt_no_abb_latest){
                        self.config.rcpt_no_abb_latest = rcpt_no_abb_latest_cache;
                        flag_update = true;
                    }
                }
                if(flag_update){
                    var fields = {};
                    fields.id = self.config.id;
                    fields.rcpt_no_abb_round= self.config.rcpt_no_abb_round;
                    fields.rcpt_no_abb_latest = self.config.rcpt_no_abb_latest;
                    try{
                        new Model('pos.config').call('update_rcpt_no_abb', [fields]);
                    }
                    catch(error){
                        console.error(error);
                    }
                }

                self.db.save('rcpt_no_abb_round', self.config.rcpt_no_abb_round);
                self.db.save('rcpt_no_abb_latest', self.config.rcpt_no_abb_latest);
            }
       },
    }
    ]);

    models.load_fields('pos.session', ['past_session', 'cash_register_balance_end']);

    basewidget.include({
        format_number: function (value) {
            if (typeof value !== 'number') {
                value = parseInt(value, 10);
            }
            return formats.format_value(value, {type: 'integer'});
        },
    });

    screens.ScreenWidget.include({
        //  8: Backspace, 46: Delete, 9: Tab, Ctrl: 17, Shift: 16, arrow 37-40, alt: 67, 0-9Numbers: 48-57
        function_key: [8, 9, 37, 38, 39, 40, 46],
        allow_number: function(event){
            if(event.target && event.target.tagName.toUpperCase() == 'INPUT') {
                if(!["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"].includes(event.key)){
                    event.preventDefault();
                }
            }
        },
        allow_with_custom: function(event, custom){
            if(event.target && event.target.tagName.toUpperCase() == 'INPUT') {
                if(!custom.includes(event.key)){
                    event.preventDefault();
                }
            }
        },
        enter_to_blur: function(event){
            if(event.key.toUpperCase() == 'Enter'.toUpperCase()){
                this.blur();
            }
        },
        barcode_product_action: function(code){
            if (code.length > 1){
                var self = this;
                if (self.pos.scan_product(code)) {
                    if (self.barcode_product_screen) {
                        self.gui.show_screen(self.barcode_product_screen);
                    }
                } else {
                    this.barcode_error_action(code);
                }
            }
        },

        // what happens when a cashier id barcode is scanned.
        // the default behavior is the following :
        // - if there's a user with a matching barcode, put it as the active 'cashier', go to cashier mode, and return true
        // - else : do nothing and return false. You probably want to extend this to show and appropriate error popup...
        barcode_cashier_action: function(code){
            if (code.length > 1){
                var users = this.pos.users;
                for(var i = 0, len = users.length; i < len; i++){
                    if(users[i].barcode === code.code){
                        this.pos.set_cashier(users[i]);
                        this.chrome.widget.username.renderElement();
                        return true;
                    }
                }
                this.barcode_error_action(code);
                return false;
            }
        },

        // what happens when a client id barcode is scanned.
        // the default behavior is the following :
        // - if there's a user with a matching barcode, put it as the active 'client' and return true
        // - else : return false.
        barcode_client_action: function(code){
            if (code.length > 1){
                var partner = this.pos.db.get_partner_by_barcode(code.code);
                if(partner){
                    this.pos.get_order().set_client(partner);
                    return true;
                }
                this.barcode_error_action(code);
                return false;
            }
        },

        // what happens when a discount barcode is scanned : the default behavior
        // is to set the discount on the last order.
        barcode_discount_action: function(code){
            if (code.length > 1){
                var last_orderline = this.pos.get_order().get_last_orderline();
                if(last_orderline){
                    last_orderline.set_discount(code.value);
                }
            }
        },
        // What happens when an invalid barcode is scanned : shows an error popup.
        barcode_error_action: function(code) {
            if (code.length > 1){
                var show_code;
                if (code.code.length > 32) {
                    show_code = code.code.substring(0,29)+'...';
                } else {
                    show_code = code.code;
                }
                this.gui.show_popup('error-barcode',show_code);
            }
        },
        select_branch_manager: function(){
            var self = this;
            var def  = new $.Deferred();
            var managers = [];
            this.pos.users.forEach(function(user){
                if(self.pos.branch.manager_user_ids.includes(user.id)){
                    managers.push({
                        'label': user.name,
                        'item':  user,
                    });
                }
            });
            if(managers.length == 0){
                self.gui.show_popup('error',{
                    'title': 'Alert',
                    'body': _t('There is no Manager on this POS configuration'),
                });
                def.reject();
            }
            else if(managers.length == 1){
                def.resolve(managers[0].item);
            }
            else {
                self.gui.show_popup('selection',{
                    'title': _t('Select Manager'),
                    list: managers,
                    confirm: function(user){ def.resolve(user); },
                    cancel:  function(){ def.reject(); },
                });
            }

            return def;
        },
	    ask_manager_ask_pin: function(){
            var self = this;
            var def = $.Deferred();
            var managers = self.select_branch_manager();

            managers.then(function(manager){
                if(!manager.pos_security_pin || manager.pos_security_pin == ""){
                    self.gui.show_popup('alert', {
                        'title': 'Alert',
                        'body': _t('The manager has not set Security Pin yet')
                    });
                    def.reject();
                }
                else{
                    self.gui.ask_password(manager.pos_security_pin).then(function(){
                        def.resolve({
                            id: manager.id,
                            datetime: (new Date()).toISOString(),
                        });
                    }, function(){ def.reject(); });
                }
            }, function(){ def.reject(); });
            return def;

	    },
    });

    screens.ClientListScreenWidget.include({
        save_client_details: function (partner) {
            var self = this;

            var fields = {};
            this.$('.client-details-contents .detail').each(function (idx, el) {
                fields[el.name] = el.value;
            });

            if (!fields.name) {
                this.gui.show_popup('error', _t('A Customer Name Is Required'));
                return;
            }

            if (this.uploaded_picture) {
                fields.image = this.uploaded_picture;
            }

            fields.id = partner.id || false;
            fields.country_id = fields.country_id || false;
            fields.barcode = fields.barcode || '';

            function nl2br(str, is_xhtml) {
                var breakTag = (is_xhtml || typeof is_xhtml === 'undefined') ? '<br />' : '<br>';
                return (str + '').replace(/([^>\r\n]?)(\r\n|\n\r|\r|\n)/g, '$1' + breakTag + '$2');
            }

            new Model('res.partner').call('create_from_ui', [fields]).then(function (partner_id) {
                self.saved_client_details(partner_id);
            }, function (err, event) {
                event.preventDefault();
                if (err.code == 200) {
                    self.gui.show_popup('error', {
                        'title': _t('Error: Could not Save Changes'),
                        'body': nl2br(_t(err.data.message)),
                    });
                } else {
                    self.gui.show_popup('error', {
                        'title': _t('Error: Could not Save Changes'),
                        'body': _t('Your Internet connection is probably down.'),
                    });
                }
            });
        },
        filter_state: function (country_id) {
            var self = this;
            var options = "<option value=''>None</option>";
            var $select = self.$('select[name="state_id"]');
            var select_val = $select.val();
            $select.html(options);
            if (country_id != "" && country_id != null) {
                var filtered_states = _.filter(self.pos.states, function (item) {
                    if (item.country_id[0] == country_id) {
                        $select.append("<option value='" + item.id + "'>" + item.name + "</option>");
                        return true;
                    }
                    return false;


                });
                $select.val(select_val);


            }
        },
        display_client_details: function (visibility, partner, clickpos) {
            this._super(visibility, partner, clickpos);
            var contents = this.$('.client-details-contents');
            var self = this;
            contents.off('change', '.company_type');
            contents.on('change', '.company_type', function () {
                var company_type = $(this).val();
                if (company_type != 'company') {
                    contents.find('.shop_id').closest('.client-detail').hide();
                } else {
                    contents.find('.shop_id').closest('.client-detail').show();
                }
            });
            contents.find('.company_type').trigger('change');
            if (visibility === 'show') {

            } else if (visibility === 'edit') {

            }


//            self.filter_state(this.$('select[name="country_id"]').val());
//            this.$('select[name="country_id"]').on('change', function (i, e) {
//                var country_id = $(this).val();
//                self.filter_state(country_id);
//
//            });

//            this.$('select[name="state_id"]').on('change', function (i, e) {
//                var state_id = $(this).val();
//            });

        },
    });

    screens.ReceiptScreenWidget.include({
        print_web: function () {
            if(this.printed){
                this.click_next();
            }
        },
        show: function(){
            this._super();
            var order = this.pos.get_order();

            if  (!(order.sequence_number in count_pos_tab)){
                count_pos_tab[order.sequence_number] = 0;
            }

            if (count_pos_tab[order.sequence_number] === 0){
                this.printed = false;

                setTimeout($.proxy(function () {
                    window.print();
                    this.printed = true;

                }, this), 1000);

                count_pos_tab[order.sequence_number] = 1;
            }
        },

    });

    screens.ProductListWidget.include({
        renderElement: function () {
            var el_str = QWeb.render(this.template, {widget: this});
            var el_node = document.createElement('div');
            el_node.innerHTML = el_str;
            el_node = el_node.childNodes[1];

            if (this.el && this.el.parentNode) {
                this.el.parentNode.replaceChild(el_node, this.el);
            }
            this.el = el_node;


            var list_container = el_node.querySelector('.product-list');
            for (var i = 0, len = this.product_list.length; i < len; i++) {

                if (this.product_list[i].hide_in_pos_product_list) {
                    continue;
                }


                var product_node = this.render_product(this.product_list[i]);
                product_node.addEventListener('click', this.click_product_handler);
                list_container.appendChild(product_node);
            }
        }
    });

    screens.OrderWidget.include({
        update_summary: function(){
            var order = this.pos.get_order();
            if (!order.get_orderlines().length) {
                return;
            }
            this._super();

            var total = order ? order.get_total_with_tax() : 0;

            var taxes = order ? total - order.get_total_without_tax() : 0;

            this.el.querySelector('.summary .total > .value').textContent = this.format_currency(total);
            this.el.querySelector('.summary .total .subentry .value').textContent = this.format_currency(taxes);
            this.el.querySelector('.total-prod').textContent = "รวม "+order.get_orderlines().length.toString()+" รายการ";
        },
    });

    PosDB.include({
        add_partners: function (partners) {
            var updated_count = this._super(partners);
            var partner;
            if (updated_count) {
                for (var id in this.partner_by_id) {
                    partner = this.partner_by_id[id];

                    if (partner.barcode) {
                        this.partner_by_barcode[partner.barcode] = partner;
                    }
                    partner.address = (partner.street || '') + ', ' +
                            (partner.street2 || '') + ', ' +
                            (partner.zip || '') + ' ' +
                            (partner.city || '') + ', ' +
                            (partner.state_id[1] || '') + ', ' +
                            (partner.country_id[1] || '');
                    this.partner_search_string += this._partner_search_string(partner);
                }
            }
            return updated_count;

        },
        pos_order_fields: function(){
            return ['id', 'name', 'date_order', 'partner_id', 'lines', 'statement_ids', 'pos_reference'
            , 'inv_no' ,'invoice_id', 'branch_id', 'session_id', 'amount_total', 'change_rounding'];
        },
        pos_order_line_fields: function(){
            return ['id', 'product_id', 'order_id', 'qty','discount','price_unit','price_tax','price_subtotal_incl'
            , 'price_subtotal'];
        },
    });

    screens.NumpadWidget.include({
        start: function () {
            this._super();
            this.$el.find('.numpad-increase').click(_.bind(this.clickIncrease, this));
            this.$el.find('.numpad-decrease').click(_.bind(this.clickDecrease, this));
            this.$el.find('.clear-order').click(_.bind(this.clickClear, this));
        },
        clickIncrease: function (event) {
            var value = event.currentTarget.attributes['data-value'].nodeValue;
            this.stepNumber(value);
        },
        clickDecrease: function (event) {
            var value = event.currentTarget.attributes['data-value'].nodeValue;
            value = -parseInt(value);
            this.stepNumber(value);
        },
        clickClear: function (event) {
            this.clearOrder();
        },
        clearOrder: function () {
            var order = this.pos.get_order();

            var selected_orderline = order.get_selected_orderline();
            order.remove_orderline(selected_orderline);
//            do {
//                var orderlines = order.get_orderlines();
//                for (var i = 0; i < orderlines.length; i++) {
//                    var orderline = orderlines[i];
//                    order.orderlines.remove(orderline);
//                }
//            } while (orderlines.length > 0);
        },
        clickAppendNewChar: function (event) {
            var order = this.pos.get_order();
            if (order.get_selected_orderline() && order.get_selected_orderline().promotion) {
                this.gui.show_popup('alert', {
                    'title': 'Alert',
                    'body': 'สินค้าโปรโมชั่นไม่สามารถเปลี่ยนแปลงจำนวนได้',
                });
                return false;
            } else if (order.get_selected_orderline() && order.get_selected_orderline().orderset) {
                this.gui.show_popup('alert', {
                    'title': 'Alert',
                    'body': 'สินค้าจัดชุดแล้วไม่สามารถเปลี่ยนแปลงจำนวนได้',
                });
                return false;
            }

            var newChar;
            newChar = event.currentTarget.innerText || event.currentTarget.textContent;
            if(newChar == '.'){
                return null;
            }else{
                return this._super(event);
            }
        },
        stepNumber: function (val) {
            var order = this.pos.get_order();
            var selected_orderline = order.get_selected_orderline();
            if (selected_orderline) {
                var new_qty = parseInt(selected_orderline.quantity) + parseInt(val);
                if (new_qty <= 0) {
                    order.remove_orderline(selected_orderline);
                } else {
                    //set_value
                    if (order.get_selected_orderline() && order.get_selected_orderline().promotion) {
                        this.gui.show_popup('alert', {
                            'title': 'Alert',
                            'body': 'สินค้าโปรโมชั่นไม่สามารถเปลี่ยนแปลงจำนวนได้',
                        });
                        return false;
                    } else if (order.get_selected_orderline() && order.get_selected_orderline().orderset) {
                        this.gui.show_popup('alert', {
                            'title': 'Alert',
                            'body': 'สินค้าจัดชุดแล้วไม่สามารถเปลี่ยนแปลงจำนวนได้',
                        });
                        return false;
                    }
                    selected_orderline.set_quantity(new_qty);
                }
            }
        }
    });

    var px_initialize = models.PosModel.prototype.initialize;
    models.PosModel = models.PosModel.extend({
        initialize: function (session, attributes) {
            px_initialize.call(this, session, attributes);
            this.db._partner_search_string = function (partner) {

                var str = partner.name;
                if (partner.barcode) {
                    str += '|' + partner.barcode;
                }
                if (partner.address) {
                    str += '|' + partner.address;
                }
                if (partner.phone) {
                    str += '|' + partner.phone.split(' ').join('');
                }
                if (partner.mobile) {
                    str += '|' + partner.mobile.split(' ').join('');
                }
                if (partner.email) {
                    str += '|' + partner.email;
                }
                if (partner.vat) {
                    str += '|' + partner.vat;
                }
                if (partner.shop_id) {
                    str += '|' + partner.shop_id;
                }
                str = '' + partner.id + ':' + str.replace(':', '') + '\n';
                return str;
            };
        },
        push_and_invoice_order: function(order){
            var self = this;
            var invoiced = new $.Deferred();

            if(!order.get_client()){
                invoiced.reject({code:400, message:'Missing Customer', data:{}});
                return invoiced;
            }

            var order_id = this.db.add_order(order.export_as_JSON());

            this.flush_mutex.exec(function(){
                var done = new $.Deferred(); // holds the mutex

                // send the order to the server
                // we have a 30 seconds timeout on this push.
                // FIXME: if the server takes more than 30 seconds to accept the order,
                // the client will believe it wasn't successfully sent, and very bad
                // things will happen as a duplicate will be sent next time
                // so we must make sure the server detects and ignores duplicated orders

                var transfer = self._flush_orders([self.db.get_order(order_id)], {timeout:30000, to_invoice:true});

                transfer.fail(function(error){
                    invoiced.reject(error);
                    done.reject();
                });

                // on success, get the order id generated by the server
                transfer.done(function(order_server_id){
                    invoiced.resolve();
                    done.resolve();
                });

                return done;

            });

            return invoiced;
        },
        find_model: function(model_name){
            return this.models.find(model=>(model.model && model.model == model_name)?true:false);
        },
    });


    var _super_orderline = models.Orderline;
    models.Orderline = models.Orderline.extend({
        initialize: function (attr, options) {
            this.discount_amount = 0;
            this.discount_amountStr = '0';
            this.iface_line_tax_included = false;

            _super_orderline.prototype.initialize.call(this, attr, options);
        },
        init_from_JSON: function (json) {
            _super_orderline.prototype.init_from_JSON.call(this, json);
            this.set_discount_amount(json.discount_amount);
            if(_.isArray(json.taxes_id) && json.taxes_id.length && this.product){
                var product_temp = _.recursiveDeepCopy(this.product);
                product_temp.taxes_id = json.taxes_id;
                this.product = product_temp;
            }
        },
        export_as_JSON: function () {
            var json = _super_orderline.prototype.export_as_JSON.call(this);
            json.discount_amount = this.discount_amount;
            json.iface_line_tax_included = this.iface_line_tax_included;
            return json;
        },
        set_discount_amount: function (discount) {
            var disc = parseFloat(discount) || 0;
            this.discount_amount = disc;
            this.discount_amountStr = '' + disc;
            this.trigger('change', this);
        },
        get_discount_amount: function () {
            return this.discount_amount;
        },
        get_discount_acount_str: function () {
            return this.discount_amountStr;
        },
        get_base_price: function () {
            var rounding = this.pos.currency.rounding;
            return round_pr((this.get_unit_price() * this.get_quantity() * (1 - this.get_discount() / 100)) - (this.get_discount_amount() * this.get_quantity()), rounding);
        },
        get_all_prices: function () {
            var price_unit = (this.get_unit_price() * (1.0 - (this.get_discount() / 100.0))) - (this.get_discount_amount());
            var taxtotal = 0;

            var product = this.get_product();
            var taxes_ids = product.taxes_id;
            var taxes = this.pos.taxes;

            var taxdetail = {};
            var product_taxes = [];

            _(taxes_ids).each(function (el) {
                product_taxes.push(_.detect(taxes, function (t) {
                    return t.id === el;
                }));
            });

            var all_taxes = this.compute_all(product_taxes, price_unit, this.get_quantity(), 0.0001);
            _(all_taxes.taxes).each(function (tax) {
                taxtotal += tax.amount;
                taxdetail[tax.id] = tax.amount;
            });

            return {
                "priceWithTax": all_taxes.total_included,
                "priceWithoutTax": all_taxes.total_excluded,
                "tax": taxtotal,
                "taxDetails": taxdetail,
            };
        },
        set_quantity: function(quantity){
            this.order.assert_editable();
            if(quantity === 'remove'){
                this.order.remove_orderline(this);
                return;
            }else{
                var quant = parseFloat(quantity) || 0;
                var unit = this.get_unit();
                if(unit){
                    if (unit.rounding) {
                        this.quantity    = round_pr(quant, unit.rounding);
                        var decimals = 0;
                        this.quantityStr = formats.format_value(round_di(this.quantity, decimals), { type: 'float', digits: [69, decimals]});
                    } else {
                        this.quantity    = round_pr(quant, 1);
                        this.quantityStr = this.quantity.toFixed(0);
                    }
                }else{
                    this.quantity    = quant;
                    this.quantityStr = '' + this.quantity;
                }
            }
            this.trigger('change',this);
        },
        check_tax: function(product){
            var tax_company;
            var tax_line;
            for (tax_company in this.pos.taxes_by_id){
                for (tax_line in product.taxes_id){
                    if (parseInt(tax_company) === parseInt(product.taxes_id[tax_line])){
                        return true;
                    }
                }
            }

            return false;
        },
        get_all_prices_by_subtotal: function (subtotal, product) {
            var taxtotal = 0;

            var taxes_ids = product.taxes_id;
            var taxes = this.pos.taxes;

            var taxdetail = {};
            var product_taxes = [];

            _(taxes_ids).each(function (el) {
                product_taxes.push(_.detect(taxes, function (t) {
                    return t.id === el;
                }));
            });

            var all_taxes = this.compute_all(product_taxes, subtotal, 1, 0.000000001);
            _(all_taxes.taxes).each(function (tax) {
                taxtotal += tax.amount;
                taxdetail[tax.id] = tax.amount;
            });

            return {
                "priceWithTax": all_taxes.total_included,
                "priceWithoutTax": all_taxes.total_excluded,
                "tax": taxtotal,
                "taxDetails": taxdetail,
            };
        },
    });

    models.Paymentline = Backbone.Model.extend({
        initialize: function(attributes, options) {
            this.pos = options.pos;
            this.order = options.order;
            this.amount = 0;
            this.selected = false;

            if(options.cashregister){
                this.cashregister = options.cashregister;

                var currency_replace = " (" + this.cashregister.currency_id[1] + ")";
                this.name = this.cashregister.journal_id[1].replace(currency_replace, "");
            }

            if (options.json) {
                this.init_from_JSON(options.json);
                return;
            }
        },
        init_from_JSON: function(json){
            this.amount = json.amount;
            this.cashregister = this.pos.cashregisters_by_id[json.statement_id];
            var currency_replace = " (" + this.cashregister.currency_id[1] + ")";
            this.name = this.cashregister.journal_id[1].replace(currency_replace, "");
        },
        //sets the amount of money on this payment line
        set_amount: function(value){
            this.order.assert_editable();
            this.amount = round_di(parseFloat(value) || 0, this.pos.currency.decimals);
            this.trigger('change',this);
        },
        // returns the amount of money on this paymentline
        get_amount: function(){
            return this.amount;
        },
        get_amount_str: function(){
            return formats.format_value(this.amount, {
                type: 'float', digits: [69, this.pos.currency.decimals]
            });
        },
        set_selected: function(selected){
            if(this.selected !== selected){
                this.selected = selected;
                this.trigger('change',this);
            }
        },
        // returns the payment type: 'cash' | 'bank'
        get_type: function(){
            return this.cashregister.journal.type;
        },
        // returns the associated cashregister
        //exports as JSON for server communication
        export_as_JSON: function(){
            return {
                name: time.datetime_to_str(new Date()),
                statement_id: this.cashregister.id,
                account_id: this.cashregister.account_id[0],
                journal_id: this.cashregister.journal_id[0],
                amount: this.get_amount()
            };
        },
        //exports as JSON for receipt printing
        export_for_printing: function(){
            return {
                amount: this.get_amount(),
                journal: this.cashregister.journal_id[1],
            };
        },
    });

    screens.PaymentScreenWidget.include({
        init: function(parent, options) {
            var self = this;
            this._super(parent, options);
            this.keyboard_keydown_handler = function(event){
                if(event.target && event.target.tagName.toUpperCase() == 'INPUT'){

                }
                else if (event.keyCode === 8 || event.keyCode === 46) { // Backspace and Delete
                    event.preventDefault();

                    // These do not generate keypress events in
                    // Chrom{e,ium}. Even if they did, we just called
                    // preventDefault which will cancel any keypress that
                    // would normally follow. So we call keyboard_handler
                    // explicitly with this keydown event.
                    self.keyboard_handler(event);
                }
            };
            this.keyboard_handler = function(event){
                var key = '';
                if(event.target && event.target.tagName.toUpperCase() == 'INPUT'){

                }
                else {
                if (event.type === "keypress") {
                    if (event.keyCode === 13) { // Enter
                            self.validate_order();
                        } else if ( event.keyCode === 190 || // Dot
                                    event.keyCode === 110 ||  // Decimal point (numpad)
                                    event.keyCode === 188 ||  // Comma
                                    event.keyCode === 46 ) {  // Numpad dot
                            key = self.decimal_point;
                        } else if (event.keyCode >= 48 && event.keyCode <= 57) { // Numbers
                            key = '' + (event.keyCode - 48);
                        } else if (event.keyCode === 45) { // Minus
                            key = '-';
                        } else if (event.keyCode === 43) { // Plus
                            key = '+';
                        }
                    } else { // keyup/keydown
                        if (event.keyCode === 46) { // Delete
                            key = 'CLEAR';
                        } else if (event.keyCode === 8) { // Backspace
                            key = 'BACKSPACE';
                        }
                    }

                    self.payment_input(key);
                    event.preventDefault();
                }
            };
        },
        renderElement: function () {
            var self = this;
            this._super();
            this.$('.js_set_customer').off('click');
        },
        show: function () {
			var self = this;
            var order = this.pos.get_order();
            order.clean_empty_orderlines();

            //clear payment line
            order.select_paymentline(undefined);
            var to_remove = order.get_paymentlines();
            for(var i = to_remove.length-1 ; i >= 0 ; i--){
                order.remove_paymentline(to_remove[i]);
            }

            self._super()
            if (!this.pos.get_order().check_cash_limit()){
                self.gui.back();
            }
            order.load_rcpt_no_abb_from_server();
        },
        order_is_valid: function(force_validation) {
            var self = this;

            var order = this.pos.get_order();

            var client = this.pos.get_client();

            var order_lines = order.get_orderlines();

            var pos_session_date = order.pos_session_date;

            var pos_session_date_stop = new Date(pos_session_date.toISOString());
            pos_session_date_stop.setDate(pos_session_date.getDate() + 2);

            var creation_date = order.creation_date

            if (order.past_session != true) {
                if (creation_date > pos_session_date_stop){

                    var timeToStamp = creation_date.toISOString().split('T')[1];

                    var dateToStamp = pos_session_date.toISOString().split('T')[0];
                    var dateTimeToStamp = new Date(dateToStamp + "T" + timeToStamp);

                    order.creation_date = dateTimeToStamp;

                }
            }

            for (var i = 0; i < order_lines.length; i++) {

                if (order_lines[i].discount_amount != 0) {
                    if (client == null) {
                        this.gui.show_popup('alert', {
                            'title': 'Alert',
                            'body': 'Please Select Customer',
                        });
                        return;
                    }
                    if (client != null && client.property_product_pricelist == null) {
                        this.gui.show_popup('alert', {
                            'title': 'Alert',
                            'body': "There Isn't PriceList In Customer",
                        });
                        return false;
                    }
                }
            }

            // FIXME: this check is there because the backend is unable to
            // process empty orders. This is not the right place to fix it.
            if (order.get_orderlines().length === 0) {
                this.gui.show_popup('error', {
                    'title': _t('Empty Order'),
                    'body': _t('There must be at least one product in your order before it can be validated'),
                });
                return false;
            }

            var plines = order.get_paymentlines();
            for (var i = 0; i < plines.length; i++) {
                if (plines[i].get_type() === 'bank' && plines[i].get_amount() < 0) {
                    this.pos_widget.screen_selector.show_popup('error', {
                        'message': _t('Negative Bank Payment'),
                        'comment': _t('You cannot have a negative amount in a Bank payment. Use a cash payment method to return money to the customer.'),
                    });
                    return false;
                }
            }

            if(Math.abs(order.get_total_with_tax()) == 0){
                this.gui.show_popup('alert', {
                    'title': 'Alert',
                    'body': 'ไม่สามารถชำระด้วยยอด 0 บาทได้ กรุณาตรวจสอบรายการอีกครั้ง',
                });
                return false;
            }

            if (!order.is_paid() || this.invoicing) {
                return false;
            }

            // The exact amount must be paid if there is no cash payment method defined.
            if (Math.abs(order.get_total_with_tax() - order.get_total_paid()) > 0.0001) {
                var cash = false;
                for (var i = 0; i < this.pos.cashregisters.length; i++) {
                    cash = cash || (this.pos.cashregisters[i].journal.type === 'cash');
                }
                if (!cash) {
                    this.gui.show_popup('error', {
                        title: _t('Cannot return change without a cash payment method'),
                        body: _t('There is no cash payment method available in this point of sale to handle the change.\n\n Please pay the exact amount or add a cash payment method in the point of sale configuration'),
                    });
                    return false;
                }
            }


            // if the change is too large, it's probably an input error, make the user confirm.
            if (!force_validation && (order.get_total_with_tax() * 1000 < order.get_total_paid()) ) {
                this.gui.show_popup('confirm', {
                    title: _t('Please Confirm Large Amount'),
                    body: _t('Are you sure that the customer wants to  pay') +
                            ' ' +
                            this.format_currency(order.get_total_paid()) +
                            ' ' +
                            _t('for an order of') +
                            ' ' +
                            this.format_currency(order.get_total_with_tax()) +
                            ' ' +
                            _t('? Clicking "Confirm" will validate the payment.'),
                    confirm: function () {
                        self.validate_order('confirm');
                    },
                });
                return false;
            }

            if(order.is_to_invoice()){
                if(client == null ){
                    self.gui.show_popup('confirm', {
                        'title': _t('Please select the Customer'),
                        'body': _t('You need to select the customer before you can invoice an order.'),
                        confirm: function () {
                            self.gui.show_screen('clientlist');
                        },
                    });
                    return false;
                }
            }

            return true;
        },
        finalize_validation: function() {
            var self = this;
            var order = this.pos.get_order();
            //remove paymentline which amount is zero
            order.clean_empty_paymentlines();

            if (order.is_paid_with_cash() && this.pos.config.iface_cashdrawer) {

                this.pos.proxy.open_cashbox();
            }

            //barcode
            order.update_inv_no();
            //render barcode image
            var canvas = document.createElement("canvas");
            JsBarcode(canvas, order.inv_no, {
                format: "CODE128",
                weight: 600,
                height: 70,
                displayValue: false,
            });
            order.barcode_inv_no = canvas;
            order.barcode_inv_no_base64 = canvas.toDataURL("image/png");

            //order.initialize_validation_date();
            order.finalized = true;
            this.amount_discount = order.get_total_discount();
            order.get_change(); //To call this function because if not call this function, field change no value.
            order.get_rounding(); //To call this function because if not call this function, field change_rounding no value.

            if (order.is_to_invoice()) {

                var invoiced = this.pos.push_and_invoice_order(order);
                this.invoicing = true;

                invoiced.fail(function (error) {
                    self.invoicing = false;
                    order.finalized = false;
                    if (error.message === 'Missing Customer') {
                        self.gui.show_popup('confirm', {
                            'title': _t('Please select the Customer'),
                            'body': _t('You need to select the customer before you can invoice an order.'),
                            confirm: function () {
                                self.gui.show_screen('clientlist');
                            },
                        });
                    } else if (error.code < 0) {        // XmlHttpRequest Errors
                        self.gui.show_popup('error', {
                            'title': _t('The order could not be sent'),
                            'body': _t('Check your internet connection and try again.'),
                        });
                    } else if (error.code === 200) {    // OpenERP Server Errors
                        self.gui.show_popup('error-traceback', {
                            'title': error.data.message || _t("Server Error"),
                            'body': error.data.debug || _t('The server encountered an error while receiving your order.'),
                        });
                    } else {                            // ???
                        self.gui.show_popup('error', {
                            'title': _t("Unknown Error"),
                            'body': _t("The order could not be sent to the server due to an unknown error"),
                        });
                    }
                });

                invoiced.done(function () {
                    self.invoicing = false;
                    self.gui.show_screen('receipt');
                });
            } else {
                this.pos.push_order(order, {timeout: 10000});
                this.gui.show_screen('receipt');
            }
            order.increase_payment_no();
            order.update_pos_config_rpct_no_abb();

            //Plus because I need to get cash_register_balance_end real time
            this.pos.pos_session.cash_register_balance_end += order.get_total_with_tax();
        },
        click_numpad: function(button) {
            var paymentlines = this.pos.get_order().get_paymentlines();
            var open_paymentline = false;

            for (var i = 0; i < paymentlines.length; i++) {
                if (! paymentlines[i].paid) {
                    open_paymentline = true;
                }
            }

            if (! open_paymentline) {

                this.pos.get_order().add_paymentline( this.pos.cashregisters[0]);
                this.render_paymentlines();
            }

            this.payment_input(button.data('action'));
        },
        add_paymentline: function(cashregister) {
            this.assert_editable();
            var newPaymentline = new models.Paymentline({},{order: this, cashregister:cashregister, pos: this.pos});
            if(this.pos.config.iface_precompute_cash){
                newPaymentline.set_amount( Math.max(this.get_due(),0) );
            }

            this.paymentlines.add(newPaymentline);
            this.select_paymentline(newPaymentline);

        },
    });

    gui.Gui.include({
        numpad_input: function(buffer, input, options) {
            var newbuf  = buffer.slice(0);
            options = options || {};
            var newbuf_float  = formats.parse_value(newbuf, {type: "float"}, 0);
            var decimal_point = _t.database.parameters.decimal_point;

            if (input === decimal_point) {
                if (options.firstinput) {
                    newbuf = "0.";
                }else if (!newbuf.length || newbuf === '-') {
                    newbuf += "0.";
                } else if (newbuf.indexOf(decimal_point) < 0){
                    newbuf = newbuf + decimal_point;
                }
            } else if (input === 'CLEAR') {
                newbuf = "";
            } else if (input === 'BACKSPACE') {
                newbuf = newbuf.substring(0,newbuf.length - 1);
            } else if (input === '+') {
                if ( newbuf[0] === '-' ) {
                    newbuf = newbuf.substring(1,newbuf.length);
                }
            } else if (input === '-') {
                if ( newbuf[0] === '-' ) {
                    newbuf = newbuf.substring(1,newbuf.length);
                } else {
                    newbuf = '-' + newbuf;
                }
            } else if (input[0] === '+' && !isNaN(parseFloat(input))) {
                newbuf = this.chrome.format_currency_no_symbol(newbuf_float + parseFloat(input));
            } else if (!isNaN(parseInt(input))) {
                if (options.firstinput) {
                    newbuf = '' + input;
                } else {
                    newbuf += input;
                }
            }

            // End of input buffer at 12 characters.
            if (newbuf.length > buffer.length && newbuf.length > 12) {
                this.play_sound('bell');
                return buffer.slice(0);
            }

            if (newbuf.indexOf(".") != -1) {
                var res = newbuf.split(".");
                newbuf = res[0] + "." + res[1].substring(0, 2);
            }


            return newbuf;
        },
    });

    var _super_order = models.Order;
    models.Order = models.Order.extend({
        get_change: function(paymentline) {
//            var total_with_tax = Math.abs(this.get_total_rounding(this.get_total_with_tax()));

            var total_with_tax = Math.abs(this.get_total_with_tax());
            var paid_with_cash = this.get_total_paid_with_cash();
            var paid_with_cash_decimal_point = paid_with_cash * 10 % 10 / 10;

            if(this.is_paid_with_cash() && [0, 0.25, 0.5, 0.75].includes(paid_with_cash_decimal_point))
                total_with_tax = total_with_tax - this.change_rounding;

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
            return round_pr(Math.max(0,change), 0.01);
        },
        get_due: function(paymentline) {
            var total_paid = this.get_total_paid();
            var total_with_tax = this.get_total_with_tax();

            if(total_paid > 0 && this.is_paid_with_cash()){
                this.get_rounding();
            }
            else{
                this.change_rounding = 0.00;
            }

            if (!paymentline) {
                var due = total_with_tax - total_paid;
            } else {
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

            if(due == 0 && this.change_rounding > 0){
                this.change_rounding = 0;
            }

            if(this.change_rounding == round_pr(due, 0.01) || this.is_paid_with_cash() &&  this.change_rounding == 0 && due > 0 && round_pr(due, 0.01) < 0.25){
                this.change_rounding = round_pr(due, 0.01);
                due = 0;
            }

            return round_pr(Math.max(0,due), 0.01);
        },
        initialize: function (attributes, options){
            Backbone.Model.prototype.initialize.apply(this, arguments);
            this.pos = options.pos;
            this.pos_session_date = new Date(this.pos.pos_session.start_at.split(' ')[0]);
            this.past_session = this.pos.pos_session.past_session;
            options = options || {};

            this.inv_no = '';
            this.rcpt_no_abb_latest;
            this.iface_tax_included = this.pos.config.iface_tax_included;
            this.amount_total_rounding = 0.00;
            this.change_rounding = 0.00;
            this.amount_discount = 0.00;

            this.load_payment_no();
            if (!options.json) {
                //  this occur when new tab
                this.login_number = this.pos.pos_session.login_number;
                if (typeof this.pos.pos_session.login_payment_no === 'undefined') {
                    this.pos.pos_session.login_payment_no = [];
                }
                if (typeof this.pos.pos_session.login_payment_no[this.login_number] === 'undefined') {
                    this.pos.pos_session.login_payment_no[this.login_number] = 1;
                }
                this.save_payment_no();

            }

            _super_order.prototype.initialize.call(this, attributes, options);

//            this.inv_no = this.get_inv_no();
            return this;

        },
        add_product: function (product, options) {
            if (this._printed) {
                this.destroy();
                return this.pos.get_order().add_product(product, options);
            }
            this.assert_editable();
            options = options || {};
            var attr = JSON.parse(JSON.stringify(product));
            attr.pos = this.pos;
            attr.order = this;
            var line_id = this.get_orderline_by_product_id(product.id);
            if (!this.pos.config.multi_line && line_id && !options.multi_line
                && (options === undefined || options.extras === undefined || options.extras.promotion === undefined || !options.extras.promotion )) {

                var orderlines = this.pos.get_order().get_orderlines();
                for(var idx = 0; idx < orderlines.length; idx++){
                    if(line_id == orderlines[idx]){
                        orderlines.push(orderlines.splice(idx, 1)[0]);
                        //re render order widget
                        var order_widget = this.pos.chrome.screens.products.order_widget;
                        if(idx+1 < orderlines.length){
                            order_widget.renderElement();
                        }
                        //scroll to bottom
                        var el_element = order_widget.el.children[0];
                        el_element.scrollTop = el_element.scrollHeight;
                        break;
                    }
                }

                this.select_orderline(line_id);
                var new_qty = parseInt(line_id.quantity) + parseInt(1);

                //set_value
                if (this.get_selected_orderline() && this.get_selected_orderline().promotion) {
                    this.gui.show_popup('alert', {
                        'title': 'Alert',
                        'body': 'สินค้าโปรโมชั่นไม่สามารถเปลี่ยนแปลงจำนวนได้',
                    });
                    return false;
                } else if (this.get_selected_orderline() && this.get_selected_orderline().orderset) {
                    this.gui.show_popup('alert', {
                        'title': 'Alert',
                        'body': 'สินค้าจัดชุดแล้วไม่สามารถเปลี่ยนแปลงจำนวนได้',
                    });
                    return false;
                }
                line_id.set_quantity(new_qty);
                //move line to the last
            }
            else {

                //initial date when add the first orderline
                if(this.get_orderlines().length == 0){
                    this.initialize_validation_date();
                }

                var line = new models.Orderline({}, {pos: this.pos, order: this, product: product});

                line.iface_line_tax_included = line.check_tax(product);

                if (options.quantity !== undefined) {
                    line.set_quantity(options.quantity);
                }
//                if (options.discount !== undefined) {
//                    line.set_discount(options.discount);
//                }
                if (options.price !== undefined) {
                    line.set_unit_price(options.price);
                }

                if (options.extras !== undefined) {
                    for (var prop in options.extras) {
                        line[prop] = options.extras[prop];
                    }
                }

                this.orderlines.add(line);
                this.select_orderline(this.get_last_orderline());

//                var last_orderline = this.get_last_orderline();
//                if (last_orderline && last_orderline.can_be_merged_with(line) && options.merge !== false) {
//                    last_orderline.merge(line);
//                } else {
//                    this.orderlines.add(line);
//                }
            }
            this.load_rcpt_no_abb_from_cache();
        },
        get_orderline_by_product_id: function(product_id){
            var orderlines = this.orderlines.models;
            for(var i = 0; i < orderlines.length; i++){
                if(orderlines[i].product.id === product_id){
                    return orderlines[i];
                }
            }
            return false;
        },
        update_inv_no: function () {
            this.inv_no = this.get_inv_no();
            this.trigger('change');
        },
        update_pos_config_rpct_no_abb: function(){
            var fields = {};
            fields.id = this.pos.config.id || false;
            var rcpt_no_abb_round = this.pos.db.load('rcpt_no_abb_round') || false;
            var rcpt_no_abb_latest = this.pos.db.load('rcpt_no_abb_latest') || false;
            if(rcpt_no_abb_round){
                fields.rcpt_no_abb_round = rcpt_no_abb_round;
            }

            if(rcpt_no_abb_latest){
                fields.rcpt_no_abb_latest = rcpt_no_abb_latest;
            }

            try{
                new Model('pos.config').call('update_rcpt_no_abb', [fields]);
            }
            catch(error){
                console.error(error);
            }
        },
        get_payment_no: function () {
//            return this.pos.pos_session.login_payment_no[this.login_number];

            this.pos.pos_session.login_payment_no[this.login_number];
//            this.load_payment_no();
            this.load_rcpt_no_abb_from_cache();
            return this.rcpt_no_abb_latest;
        },
        get_inv_no: function () {
            function zero_pad(num, size) {
                var s = "" + num;
                while (s.length < size) {
                    s = "0" + s;
                }
                return s;
            }

            var now = new Date();
            var prefix_year = now.getFullYear().toString().slice(2,4);
            var prefix_month = zero_pad((now.getMonth() + 1).toString(), 2); //.getMonth() Returns the month (from 0-11)
            var terminal_no = this.pos.config.terminal_no || 1;
            var branch_id = this.pos.branch.branch_id || '000';
            var payment_no = zero_pad(this.get_payment_no(), 5);
            var session_name = this.pos.pos_session.name;
            var login_number = zero_pad(this.login_number, 2);
            //var inv_no_temp = terminal_no + session_name + login_number + '-' + payment_no;
            var inv_no_temp = terminal_no + '-' + prefix_year + prefix_month + payment_no;
            return inv_no_temp

        },
        init_from_JSON: function (json) {
            this.login_number = json.login_number;
            this.inv_no = json.inv_no;
            this.iface_tax_included = json.iface_tax_included;
            this.change_rounding = json.change_rounding;
            this.amount_total_rounding = json.amount_total_rounding;
            this.before_rounding = json.before_rounding;
            this.change_rounding = json.change_rounding;
            this.amount_discount = json.amount_discount;
            _super_order.prototype.init_from_JSON.call(this, json);
        },
//        finalize: function () {
//            this.pos.pos_session.payment_no++;
//            _super_order.prototype.finalize.call(this);
//        },
        export_as_JSON: function () {
            var data = _super_order.prototype.export_as_JSON.call(this);
            data.login_number = this.login_number;
            data.inv_no = this.inv_no;
            data.iface_tax_included = this.iface_tax_included;
            data.amount_total_rounding = this.amount_total_rounding;
            data.before_rounding = this.get_total_with_tax();
            data.change_rounding = this.change_rounding;
            data.amount_discount = this.amount_discount;

            var total_products = this.get_total_products_vat_nonvat();
            data.total_products_nonvat = total_products.nonvat;
            data.total_products_vat_included = total_products.vat_excluded;
            data.total_products_vat_excluded = total_products.vat_included;
            data.total_products_vat_amount = total_products.vat_amount;

            return data;
        },
        increase_payment_no: function () {
            this.pos.pos_session.login_payment_no[this.login_number]++;
//            this.load_payment_no();
            this.load_rcpt_no_abb_from_cache();
            this.rcpt_no_abb_latest = this.rcpt_no_abb_latest + 1;
            if (this.rcpt_no_abb_latest > 99999 || this.rcpt_no_abb_latest == 0){
                //reset number
                this.rcpt_no_abb_latest = 1;
                this.pos.db.save('rcpt_no_abb_latest', this.rcpt_no_abb_latest);
                // increase round
                this.pos.db.save('rcpt_no_abb_round', this.pos.db.load('rcpt_no_abb_round', 0) + 1);
            }
            //this with save 'this.rcpt_no_abb_latest to cache'
            this.save_payment_no();
        },
        clear_payment_no: function () {
            this.pos.pos_session.login_payment_no = [];
            this.save_payment_no();
        },
        load_rcpt_no_abb_from_cache: function(){
            var rcpt_no_abb_latest = this.pos.db.load('rcpt_no_abb_latest');
            this.rcpt_no_abb_latest = rcpt_no_abb_latest;
            return rcpt_no_abb_latest;
        },
        load_rcpt_no_abb_from_server: function() {
            var self = this;
            try{
                new Model('pos.config')
                .query(['rcpt_no_abb_round', 'rcpt_no_abb_latest'])
                .filter([["id", "=", self.pos.config.id]])
                .first()
                .then(function(result) {
                    if(result){
                        var rcpt_no_abb_round_cache = self.pos.db.load('rcpt_no_abb_round', 0);
                        var rcpt_no_abb_latest_cache = self.pos.db.load('rcpt_no_abb_latest', 1)

                        var rcpt_no_abb_round_db = result.rcpt_no_abb_round;
                        var rcpt_no_abb_latest_db = result.rcpt_no_abb_latest;
                        if(rcpt_no_abb_round_cache === undefined || rcpt_no_abb_round_cache < rcpt_no_abb_round_db ){
                            rcpt_no_abb_round_cache = rcpt_no_abb_round_db;
                            rcpt_no_abb_latest_cache = rcpt_no_abb_latest_db;
                        }
                        else if(rcpt_no_abb_round_cache == rcpt_no_abb_round_db && rcpt_no_abb_latest_db > rcpt_no_abb_latest_cache){
                            rcpt_no_abb_latest_cache = rcpt_no_abb_latest_db;
                        }
                        else{
                            //case cache is greater than db
                            self.update_pos_config_rpct_no_abb();
                        }
                        self.pos.db.save('rcpt_no_abb_round', rcpt_no_abb_round_cache);
                        self.pos.db.save('rcpt_no_abb_latest', rcpt_no_abb_latest_cache);
                        self.pos.config.rcpt_no_abb_round = rcpt_no_abb_round_cache;
                        self.pos.config.rcpt_no_abb_latest = rcpt_no_abb_latest_cache;
                        //update to the order
                        self.pos.get_order().rcpt_no_abb_latest = rcpt_no_abb_latest_cache;
                    }
                });
            }
            catch(error){
                console.error(error);
            }
        },
        load_payment_no: function () {

            var load_session_id = this.pos.db.load('session_id');
            var session_id = this.pos.pos_session.id;
            if (load_session_id != session_id) {
                this.pos.db.save('session_id', session_id);
                this.clear_payment_no();
            }

            this.pos.pos_session.login_payment_no = this.pos.db.load('login_payment_no');

            if (typeof this.pos.db.cache.rcpt_no_abb_round === 'undefined'){
                this.pos.db.save('rcpt_no_abb_round', 0);
            }

            if (typeof this.pos.db.cache.rcpt_no_abb_latest === 'undefined'){
                this.pos.db.save('rcpt_no_abb_latest', 1);
            }

            var rcpt_no_abb_round_cache = this.pos.db.load('rcpt_no_abb_round');
            var rcpt_no_abb_round_db = this.pos.config.rcpt_no_abb_round;
            var rcpt_no_abb_latest_cache = this.pos.db.load('rcpt_no_abb_latest');
            var rcpt_no_abb_latest_db = this.pos.config.rcpt_no_abb_latest;

            //precheck with currently cache and config
            if(rcpt_no_abb_round_cache < rcpt_no_abb_round_db ){
                rcpt_no_abb_latest_cache = rcpt_no_abb_latest_db;
            }
            else if(rcpt_no_abb_round_cache == rcpt_no_abb_round_db && rcpt_no_abb_latest_db > rcpt_no_abb_latest_cache){
                rcpt_no_abb_latest_cache = rcpt_no_abb_latest_db;
            }
            this.rcpt_no_abb_latest = rcpt_no_abb_latest_cache;
            this.load_rcpt_no_abb_from_server();
        },
        save_payment_no: function () {
            this.pos.db.save('login_payment_no', this.pos.pos_session.login_payment_no);
            this.pos.db.save('rcpt_no_abb_latest', this.rcpt_no_abb_latest);
            this.pos.config.rcpt_no_abb_latest = this.rcpt_no_abb_latest;
        },
        get_orderline_count: function () {
            return this.orderlines.length()
        },
        get_subtotal: function () {
            return round_pr(this.orderlines.reduce((function (sum, orderLine) {
                return sum + (orderLine.price * orderLine.quantity);
            }), 0), 0.0001);
        },
        get_total_discount: function () {
            return round_pr(this.orderlines.reduce((function (sum, orderLine) {
                return sum + (orderLine.get_unit_price() * (orderLine.get_discount() / 100) * orderLine.get_quantity()) + (orderLine.get_discount_amount() * orderLine.get_quantity());
            }), 0), 0.001);
        },
        get_total_paid: function() {
            return round_pr(this.paymentlines.reduce((function(sum, paymentLine) {
                return sum + paymentLine.get_amount();
            }), 0), 0.01);
        },
        get_total_paid_with_cash: function(){
            return round_pr(this.paymentlines.reduce((function(sum, paymentLine) {
                if(paymentLine.cashregister.journal.type == 'cash')
                    return sum + paymentLine.get_amount();
                else
                    return sum;
            }), 0), 0.01);
        },
        get_total_without_tax: function() {
            return round_pr(this.orderlines.reduce((function(sum, orderLine) {
                return sum + round_pr(orderLine.get_price_without_tax(), 0.0001);
            }), 0), 0.001);
        },
        get_tax: function(){
            return round_pr(this.orderlines.reduce((function(sum, orderLine) {
                return sum + orderLine.get_all_prices().tax;
                this.get_all_prices();
            }), 0), 0.001);
        },
        get_total_with_tax: function() {
            return round_pr((this.get_total_without_tax() + this.get_total_tax()), 0.01);
        },
        get_total_tax: function() {
            return round_pr(this.orderlines.reduce((function(sum, orderLine) {
                return sum + round_pr(orderLine.get_tax(), 0.0001);
            }), 0), 0.0001);
        },
        get_total_rounding: function(total){
            var total_integer = parseInt(total);
            var total_decimal = total - total_integer;

            if (total_decimal > 0.75){
                this.amount_total_rounding = total_integer + 0.75;
            }
            else if (total_decimal > 0.50 && total_decimal < 0.75){
                this.amount_total_rounding = total_integer + 0.50;
            }
            else if (total_decimal > 0.25 && total_decimal < 0.50){
                this.amount_total_rounding = total_integer + 0.25;
            }
            else if (total_decimal > 0.00 && total_decimal < 0.25){
                this.amount_total_rounding = total_integer;
            }
            else{
                this.amount_total_rounding = total;
            }

            if (round_pr(this.get_total_paid(), 0.01) === round_pr(total, 0.01)){
                this.amount_total_rounding = this.get_total_paid();
            }

            return this.amount_total_rounding;
        },
        get_rounding: function(){
            if(!this.is_paid_with_cash()){
                this.change_rounding = 0.00;
                return this.change_rounding;
            }
            var total_paid = this.get_total_paid();
            if(total_paid == 0){
                this.change_rounding = 0.00;
                return this.change_rounding;
            }
            var total_before = Math.abs(this.get_total_with_tax());
            var total_rounding = Math.abs(this.get_total_rounding(total_before));

            if (round_pr(this.get_total_paid(), 0.01) === round_pr(total_before, 0.01)){
                this.change_rounding = 0.00;
            }
            else{
                this.change_rounding = Math.abs(round_pr(Math.abs(total_before) - Math.abs(total_rounding), 0.01));
            }
            return round_di(this.change_rounding, 2);
        },
        add_paymentline: function(cashregister) {
            this.assert_editable();
            var newPaymentline;
            var paymentlines = this.pos.get_order().get_paymentlines();
            var flag_payment_type_added = false;
            var amount_paid = 0.00;
            var amount_total = 0.00;

            for(var payment_type in paymentlines){
                amount_total = this.get_due(paymentlines[payment_type]);
                amount_paid = paymentlines[payment_type].get_amount();

                if (cashregister.journal_id[0] === paymentlines[payment_type].cashregister.journal_id[0]){
                    flag_payment_type_added = true;
                    newPaymentline = paymentlines[payment_type];

                    break;
                }
            }

            if ((amount_paid === 0 || amount_paid < amount_total) && !flag_payment_type_added){
                flag_payment_type_added = false;
            }
            else{
                flag_payment_type_added = true;
            }

            if (paymentlines.length === 0 || !flag_payment_type_added){
                newPaymentline = new models.Paymentline({},{order: this, cashregister:cashregister, pos: this.pos});
                if( this.pos.config.iface_precompute_cash){
                    newPaymentline.set_amount( Math.max(this.get_due(),0) );
                }
            }

            if (!flag_payment_type_added){
                if(cashregister.journal.type == 'cash'){
                    this.paymentlines.add(newPaymentline);
                }
                else{
                    this.paymentlines.unshift(newPaymentline);
                }
            }

            this.select_paymentline(newPaymentline);

        },
        get_total_remain: function(){
            var order = this;
            var subtotal = Math.abs(this.get_subtotal());
            var paymentlines = this.get_paymentlines();
            var total_payment_amount = 0.0;
            paymentlines.forEach(function(pline){
                total_payment_amount += pline.get_amount();
            });
            return subtotal - total_payment_amount;
        },
        clean_empty_orderlines: function(){
            var order = this;
            var line_to_remove = [];
            order.get_orderlines().forEach(function(line){
                  if(line.quantity == 0){
                      line_to_remove.push(line);
                  }
            });
            line_to_remove.forEach(function(line){
                order.remove_orderline(line);
            });
        },
        get_total_products_vat_nonvat: function(include_prorate = false) {

            var total_products = {
                nonvat: 0,
                vat_included: 0,
                vat_excluded: 0,
                vat_amount: 0,
            }

            this.get_orderlines().forEach(function(orderLine) {
                var price_wo_discount = orderLine.price * orderLine.quantity;
                if(include_prorate){
                    price_wo_discount -= orderLine.prorate_amount;
                }
                var all_price = orderLine.get_all_prices_by_subtotal(price_wo_discount, orderLine.product);

                if(all_price.priceWithTax != all_price.priceWithoutTax){
                    total_products.vat_included += all_price.priceWithTax;
                    total_products.vat_excluded += all_price.priceWithoutTax;
                }
                else{
                    total_products.nonvat += all_price.priceWithoutTax;
                }
            });

            total_products.vat_amount = total_products.vat_included - total_products.vat_excluded;
            return total_products;
        },
    });

    screens.ActionpadWidget.include({
        check_lot: function(self){
            var order = self.pos.get_order();
            var has_valid_product_lot = _.every(order.orderlines.models, function(line){
                return line.has_valid_product_lot();
            });
            if(!has_valid_product_lot){
                self.gui.show_popup('confirm',{
                    'title': _t('Empty Serial/Lot Number'),
                    'body':  _t('One or more product(s) required serial/lot number.'),
                    confirm: function(){
                        self.change_page(self);
                    },
                });
                return false;
            }else{
                return true;
            }
        },
        change_page: function(self){
            self.gui.show_screen('payment');
        },
        click_pay: function(self){
            var order = self.pos.get_order();
            order.clean_empty_orderlines();
            if(order.get_orderlines().length == 0){
                return;
            }
            if(!self.check_lot(self)){
                return;
            }
            self.change_page(self);
        },
        renderElement: function() {
            var self = this;
            this._super();

            this.$('.pay').off();
            this.$('.pay').click(function(){
                self.click_pay(self);
            });
        },
    });
});

