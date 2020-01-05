odoo.define('pos_credit_card.credit_card', function (require) {
    "use strict";

    var core = require('web.core');
    var screens = require('point_of_sale.screens');
    var gui = require('point_of_sale.gui');
    var formats = require('web.formats');
    var models = require('point_of_sale.models');
    var _t = core._t;

    var QWeb = core.qweb;

    models.load_fields('account.journal', ['is_credit_card']);


    var paymentline_proto = models.Paymentline.prototype;

    models.Paymentline = models.Paymentline.extend({
        initialize: function(attributes, options) {
            var self = this;
            self.is_credit_card = false;
            self.credit_card_no = '';
            self.credit_card_type = '';
            self.credit_card_no_encrypt = '';
            self.approve_code = '';

            if(options.cashregister){
                this.cashregister = options.cashregister;
                this.is_credit_card = this.cashregister.journal.is_credit_card;
            }

            paymentline_proto.initialize.call(this, attributes, options);
        },
        init_from_JSON: function(json){
            var self = this;
            paymentline_proto.init_from_JSON.call(this, json);
            self.is_credit_card = json.is_credit_card;
            self.credit_card_no = json.credit_card_no;
            self.credit_card_type = json.credit_card_type;
            self.credit_card_no_encrypt = self.encrypt_credit_card(json.credit_card_no);
            self.approve_code = json.approve_code;
        },
        // returns the associated cashregister
        //exports as JSON for server communication
        export_as_JSON: function(){
            var self = this;
            var loaded = paymentline_proto.export_as_JSON.call(this);
            loaded.is_credit_card = self.is_credit_card;
            loaded.credit_card_no = self.credit_card_no;
            loaded.credit_card_type = self.credit_card_type;
            loaded.credit_card_no_encrypt = self.encrypt_credit_card(self.credit_card_no);
            loaded.approve_code = self.approve_code;
            return loaded;
        },
        get_index: function(line){
            var index = -1;
            this.pos.get_order().get_paymentlines().forEach(function (item, idx){
                if(item === line){
                    index = idx;
                }
            });
            return index;
        },
        encrypt_credit_card: function(number){
            if(!_.isString(number))
                number = '' + number;
            if(number.length < 16)
                return "XXXXXXXXXXXXXXXX";
            else
                return number.substring(0, 6) +"XXXXXX" + number.substring(12, 16);
        },
    });

    screens.PaymentScreenWidget.include({
        credit_card_types:['VISA', 'MAST', 'TPNC', 'JCB', 'KBANK', 'CUPC', 'QKBN'],

        order_paymentlines: function(){
            var self = this;
            let paymentlines = self.pos.get_order().get_paymentlines();
            self.pos.get_order().paymentlines.models = _.sortBy(paymentlines, function(o) { 
                return o.t1cc_barcode == ""; 
            });
        },

        render_paymentlines: function(){
            var self = this;
            var contents = $('.paymentlines-container');
            this.order_paymentlines();
            this._super();

            //event allow number
            contents.off('keypress', '.only_number');
            contents.on('keypress', '.only_number',function(event){
                self.allow_number(event);
            });

            contents.on('change paste keyup keypress keydown', 'input.credit_card_no_class', function(event){
                if(event.target && event.target.tagName.toLowerCase() == 'input'){
                    $(this).val( $(this).val().replace(/\D/g, '') );
                    var order = self.pos.get_order();
                    var paymentline = order.get_paymentlines()[$(this).attr('index')];
                    paymentline.credit_card_no = $(this).val();
                    paymentline.credit_card_no_encrypt = paymentline.encrypt_credit_card(paymentline.credit_card_no);
                    order.trigger('change');
                    order.save_to_db();
                }
            });
            contents.on('change paste keyup', 'input.approve_code_class', function(event){
                if(event.target && event.target.tagName.toLowerCase() == 'input'){
                    var order = self.pos.get_order();
                    order.get_paymentlines()[$(this).attr('index')].approve_code = $(this).val()+'';
                    order.save_to_db();
                }
            });
            contents.on('change', 'select.credit_card_type_class', function(event){
                if(event.target && event.target.tagName.toLowerCase() == 'select'){
                    var order = self.pos.get_order();
                    order.get_paymentlines()[$(this).attr('index')].credit_card_type = $(this).val();
                    order.trigger('change');
                    order.save_to_db();
                }
            })
        },
        order_is_valid: function(force_validation) {
            var self = this;
            var paymentlines = self.pos.get_order().get_paymentlines();
            var list_of_credit_card_no = [];
            for(var idx = 0; idx < paymentlines.length; idx++){
                var paymentline = paymentlines[idx];
                if (paymentline.cashregister.journal.is_credit_card) {
                    if(paymentline.credit_card_no.length < 16){
                        self.gui.show_popup('alert', {
                            'title': 'Alert',
                            'body': _t('Credit Card is required 16 digits'),
                        });
                        return false;
                    }
                    else{
                        //prepare for printing
                        paymentline.credit_card_no_encrypt = paymentline.encrypt_credit_card(paymentline.credit_card_no);
                    }
                    if(paymentline.approve_code.length < 6){
                        self.gui.show_popup('alert', {
                            'title': 'Alert',
                            'body': _t('Approve Code is required 6 digits'),
                        });
                        return false;
                    }
                    if(paymentline.credit_card_type == ''){
                        self.gui.show_popup('alert', {
                            'title': 'Alert',
                            'body': _t('Type of Credit card is required'),
                        });
                        return false;
                    }
                    if(list_of_credit_card_no.includes(paymentline.credit_card_no)){
                        self.gui.show_popup('alert', {
                            'title': 'Alert',
                            'body': _t('Credit card no. ')+paymentline.credit_card_no +_t(' is duplicated'),
                        });
                        return false;
                    }
                    else{
                        list_of_credit_card_no.push(paymentline.credit_card_no);
                    }
                }
            }
            return this._super(force_validation);
        },
    });


    var _super_order = models.Order;
    models.Order = models.Order.extend({
        add_paymentline: function(cashregister) {
            this.assert_editable();
            if(cashregister.journal.type == 'bank'){
                var newPaymentline = new models.Paymentline({},{order: this, cashregister:cashregister, pos: this.pos});
                if(cashregister.journal.type !== 'cash' || this.pos.config.iface_precompute_cash){
                    newPaymentline.set_amount( Math.max(this.get_due(),0) );
                }
                this.paymentlines.unshift(newPaymentline);
                this.select_paymentline(newPaymentline);
            }
            //return and void case for t1c
            else if(cashregister.journal.redeem_type_id){
                var newPaymentline = new models.Paymentline({},{order: this, cashregister:cashregister, pos: this.pos});
                newPaymentline.set_amount( Math.max(this.get_due(),0) );
                this.paymentlines.unshift(newPaymentline);
                this.select_paymentline(newPaymentline);
            }
            else{
                _super_order.prototype.add_paymentline.call(this, cashregister);
            }
        }
    });
});
