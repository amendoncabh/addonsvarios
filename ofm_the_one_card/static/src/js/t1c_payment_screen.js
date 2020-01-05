odoo.define('ofm_the_one_card.t1c_payment_screen', function (require) {
    "use strict";

    var PosBaseWidget = require('point_of_sale.BaseWidget');
    var models = require('point_of_sale.models');
    var PosDB = require('point_of_sale.DB');

    var gui = require('point_of_sale.gui');
    var screens = require('point_of_sale.screens');
    var core = require('web.core');
    var popups = require('point_of_sale.popups');
    var QWeb = core.qweb;
    var _t = core._t;
    var Model = require('web.DataModel');
    var t1c = require('ofm_the_one_card.the_one_card')

    screens.PaymentScreenWidget.include({

        set_no_change: function() {
            var self = this;
            var order = self.pos.get_order();
            if (order.selected_paymentline) {
                var is_t1cc = Boolean(order.selected_paymentline.t1cc_barcode);
                var is_t1cp = Boolean(order.selected_paymentline.t1cp_receipt_no);
                if(!(is_t1cc || is_t1cp)){
                    self._super();
                }
            }else{
                self._super();
            }          
        },
        click_numpad: function(button) {
            var self = this;
            var order = self.pos.get_order();
            // console.log(order.selected_paymentline);
            if (order.selected_paymentline) {
                var is_t1cc = Boolean(order.selected_paymentline.t1cc_barcode);
                var is_t1cp = Boolean(order.selected_paymentline.t1cp_receipt_no);
                if (!(is_t1cc || is_t1cp)) {
                    self._super(button);
                }
            }else{
                self._super(button);
            } 
        },
        click_delete_paymentline: function(cid){
            var lines = this.pos.get_order().get_paymentlines();
            var is_t1cp = _.filter(lines, function(line){return Boolean(line.t1cp_receipt_no) && (line.cid === cid);});
            
            if (is_t1cp.length !== 0){
                this.cancel_redeem_tender(is_t1cp[0]);
            } else {
                this._super(cid);
            }
        },

        in_process: false,

        cancel_redeem_tender: function(payment_line){
            // console.log(payment_line);
            var self = this;
            self.in_process = true;

            //order information
            var order = self.pos.get_order();
            const branch = self.pos.branch;
            const receipt_no = order.get_inv_no();
            const pos_no = self.pos.config.pos_no;
            const store_no = "SOFC" + branch.branch_code;

            //member info
            const member_info = order.membercard;
            var phone_no = member_info.phone.replace || '';
            const card_no = member_info.the_one_card_no || ''; 
            const national_id = '';  
            
            //if card number is set then set phone number to empty string
            (card_no) ? phone_no = '' : phone_no = phone_no;

            var product_items = []
            var transactions = payment_line.transactions

            $.each(transactions, function(idx, transaction){
                product_items.push({
                    "productName" : transaction["productName"],
                    "transactionNo" : transaction["transactionNo"],
                });
            });

            const t1cp_receipt_no = payment_line.t1cp_receipt_no;

            //t1c info
            const t1c_config = self.pos.the_1_config;
            const t1c_url = t1c_config.T1CCnclRedeemSrv.url;
            const method = t1c_config.T1CCnclRedeemSrv.method;
            const business_date = moment().format("DDMMYYYY");
            const header = self.gui.popup_instances.api_widget.get_request_header(new Date());
            const body = {
                "phoneNo": phone_no, //phone_no will be an empty string if card_no is set
                "cardNo": card_no,
                "nationalID": national_id, //national_id will be an empty string
                "businessDate": business_date,
                "productItems": product_items,
                "receiptNo": receipt_no,
                "posNo": pos_no,
                "storeNo": store_no,
                "siebelRedeemReceiptNo": t1cp_receipt_no,
            }

            var cancel_success = function(data, status, xhr) {
                self.chrome.loading_hide();
                const body = JSON.parse(data.body);
                const ISC_firstchar = body.integrationStatusCode.charAt(0);
                const display_error = body.displayErrorMessage;
                if (ISC_firstchar === "0") {
                    const response_header = data.headers;
                    const response_body = body.responseBody;
                    console.log(response_body);
                    order.membercard.balance_points = response_body.pointsAfter;
                    order.remove_paymentline(payment_line);
                    self.reset_input();
                    self.render_paymentlines();
                    return;
                }
                else {
                    self.gui.show_popup('my_message',{
                        'title': _t('Warning'),
                        'body': _t(display_error),
                    });                         
                }
                self.in_process = false;
            };            
            //enter loading_screen
            self.chrome.loading_show();
            self.chrome.loading_message('กำลังประมวลผล', 0.8);
            $.ajax({
                url: self.pos.cors_proxy,
                type: method,
                data: JSON.stringify(body),
                dataType: 'json',
                contentType: 'application/json',
                secure: true,
                headers: _.extend(header, {'Target-URL': t1c_url}),
                success: cancel_success,
                error: self.gui.popup_instances.api_widget.handle_error,
            });
        },
        click_t1cc_line: function(id, params) {
            //add t1cc line and render lines
            var barcode = params.barcode || "";
            var amount = params.amount || 0;
            var cashregister = null;
            for ( var i = 0; i < this.pos.cashregisters.length; i++ ) {
                if ( this.pos.cashregisters[i].journal_id[0] === id ){
                    cashregister = this.pos.cashregisters[i];
                    break;
                }
            }
            let options = {
                'code' : barcode,
                'amount' : amount,
            };
            this.pos.get_order().add_t1c_line(cashregister, options);
            this.reset_input();
            this.render_paymentlines();
        },
        get_latest_point_template: function(){
            self = this;
            let point_template = self.pos.point_templates_by_id;
            if (!_.isEmpty(point_template)) {
                let sorted_by_date = _.sortBy( point_template, 'create_date' );
                let latest_template = sorted_by_date.pop();
                return latest_template;
            }
        },
        display_point_redeem: function(data_id){         
            self = this;
            var latest_point_template = self.get_latest_point_template();
            var latest_point_template_lines = latest_point_template.point_template_line_ids;
            //remove lines which have more points than the customer has
            const customer_point_balance = self.pos.get_order().membercard.balance_points;
            latest_point_template_lines = _.filter(latest_point_template_lines, function(line){
                let allow_line = line.points <= customer_point_balance;
                return allow_line;
            });
            self.chrome.loading_hide();
            self.gui.show_popup('point_template_popup', {
                'title': _t('Redeem Points (' + latest_point_template.name + ')'),
                'lines': latest_point_template_lines,
                'data_id': data_id,
            });       
        },
        verify_member: function(data_id){
            var self = this;

            //gather all necessary values for parameters
            self.chrome.loading_show();
            //order information
            const order = self.pos.get_order();
            const branch = self.pos.branch;

            //member info
            const member_info = order.membercard;
            var phone_no = member_info.phone.replace("N/A", "") || '';
            const card_no = member_info.the_one_card_no || ''; 
            const national_id = '';

            //if card number is set then set phone number to empty string
            (card_no) ? phone_no = '' : phone_no = phone_no;
            self.chrome.loading_message('กำลังประมวลผล', 0.4);
            //t1c info
            const t1c_config = self.pos.the_1_config;
            const t1c_url = t1c_config.T1CVfyMemSrv.url;
            const method = t1c_config.T1CVfyMemSrv.method;

            const header = self.gui.popup_instances.api_widget.get_request_header(new Date());
            const body = {
                "phoneNo": phone_no, //phone_no will be an empty string if card_no is set
                "cardNo": card_no,
                "nationalID": national_id, //national_id will be an empty string
            }      
            
            self.chrome.loading_message('กำลังประมวลผล', 0.5);

            var verify_success = function(data, status, xhr) {
                // self.chrome.loading_hide();
                const body = JSON.parse(data.body);
                const response_body = body.responseBody;
                const ISC_firstchar = body.integrationStatusCode.charAt(0);
                const display_error = body.displayErrorMessage;
                if (ISC_firstchar === "0") {
                    const response_header = data.headers;
                    const verify_targettransid = response_header.targettransid;
                    const member = response_body.members[0];
                    const member_status = member.memberStatus === "Active";
                    if (member_status) {
                        //keep target transactionid for redeeming points
                        order['verify_targettransid'] = verify_targettransid;
                        //step two: send otp if not verified yet, else open point redeem popup
                        if (!order.otp_verified){
                            self.otp_request(data_id);
                        }
                        else {
                            self.display_point_redeem(data_id);
                        }
                    }
                    else {
                        //show popup for member not available
                        self.gui.show_popup('my_message',{
                            'title': _t('Warning'),
                            'body': _t("Member is currently not active."),
                        }); 
                    }
                }
                else {
                    self.gui.show_popup('my_message',{
                        'title': _t('Warning'),
                        'body': _t(display_error),
                    });                    
                }
            };

            var latest_point_template = self.get_latest_point_template();

            if (latest_point_template) {
                //make API request
                self.gui.popup_instances.api_widget.make_request(self.pos.cors_proxy, method, _.extend(header,{'Target-URL': t1c_url}), body, verify_success);
            }
            else {
                self.chrome.loading_hide();
                self.gui.show_popup('my_message',{
                    'title': _t('Warning'),
                    'body': _t("Please set a point template for the following branch: " + self.pos.branch.branch_name),
                }); 
            }

        },
        otp_request: function(data_id) {
            var self = this;
            self.chrome.loading_message('กำลังประมวลผล', 0.8);
            //order information
            var order = self.pos.get_order();

            //member info
            const member_info = order.membercard;
            const card_no = member_info.the_one_card_no; 
            const is_T1C_member = "Y";

            //t1c info
            const t1c_config = self.pos.the_1_config;
            const t1c_url = t1c_config.BSReqOTPSrv.url;
            const method = t1c_config.BSReqOTPSrv.method;
            const header = self.gui.popup_instances.api_widget.get_request_header(new Date());

            const body = {
                "cardNo": card_no,
                "isT1CMember": is_T1C_member,
            };
            var otp_request_success = function(data, status, xhr) {
                self.chrome.loading_hide();
                let response_body = JSON.parse(data.body);
                let ISC_firstchar = response_body.integrationStatusCode.charAt(0);
                let display_error = response_body.displayErrorMessage;
                if (ISC_firstchar === "0") {
                    let response_header = data.headers;
                    let otp_targettransid = response_header.targettransid;
                    order.otp = {
                        "otpRefText": response_body.otpRefText,
                        "OTPSysID": otp_targettransid,
                    };
                    //display popup
                    var max_no_tries = 3
                    self.pos.gui.show_popup('otp_popup', {
                        'title': _t('OTP Verify'),
                        'no_tries': _t('0'),
                        'otp_ref_text': _t(response_body.otpRefText),
                        'status': _t(''),
                        'data_id': data_id,
                    });
                }
                else {
                    self.gui.show_popup('my_message',{
                        'title': _t('Warning'),
                        'body': _t(display_error),
                    });                       
                }
            };
            self.gui.popup_instances.api_widget.make_request(self.pos.cors_proxy, method, _.extend(header,{'Target-URL': t1c_url}), body, otp_request_success);
        },
        check_t1c_flags: function(id) {
            //check if tender method has the t1cc flag
            var cashregister = null;
            for ( var i = 0; i < this.pos.cashregisters.length; i++ ) {
                if ( this.pos.cashregisters[i].journal_id[0] === id ){
                    cashregister = this.pos.cashregisters[i];
                    break;
                }
            }
            let redeem_type = cashregister.journal.redeem_type_id;
            // console.log(redeem_type);
            if (redeem_type) {
                var is_t1cc = redeem_type.code === "T1CC" ? redeem_type.active : false;
                var is_t1cp = redeem_type.code === "T1CP" ? redeem_type.active : false;
                var is_t1ac = redeem_type.code === "T1AC" ? redeem_type.active : false;
                var journal_name = cashregister.journal_id[1];
            }
            return {
                'is_tlcc': is_t1cc, 
                'is_t1cp': is_t1cp, 
                'is_t1ac': is_t1ac,
                'journal_name': journal_name,
            };
        },
        render_paymentmethods: function() {
            var self = this;
            var methods = $(QWeb.render('PaymentScreen-Paymentmethods', { widget:this }));
                methods.on('click','.paymentmethod',function(){
                    const data_id = $(this).data('id');
                    const check_flag = self.check_t1c_flags(data_id);
                    const is_t1cc = check_flag.is_tlcc;
                    const is_t1cp = check_flag.is_t1cp;
                    const is_t1ac = check_flag.is_t1ac;
                    const journal_name = check_flag.journal_name;
                    if (is_t1cc) {
                        self.gui.show_popup('cash_coupon_popup',{
                            title: journal_name,
                            confirm: function() {
                                let barcode = this.$('#cash-coupon-barcode').val();
                                let amount = this.$('#cash-coupon-amount').val();
                                if (self.pos.get_order().get_due() >= amount){
                                    let data_pass = {'barcode': barcode, 'amount': amount};
                                    self.click_t1cc_line(data_id, data_pass);
                                    this.gui.close_popup();
                                } else {
                                    this.$('#alert').html('Tender amount should be < or = to due amount.')
                                }
                            },
                        });
                    } 
                    else if (is_t1cp){
                        self.verify_member(data_id); //passing clicked payment method
                    }
                    else if (is_t1ac){
                        const journal_name = check_flag['journal_name'];
                        self.gui.show_popup('e_cash_coupon_popup',{
                            title: journal_name,
                        });
                    }
                    else {
                        self.click_paymentmethods(data_id);
                    }
                });
            return methods;
        },
        hide_show_t1c: function(){
            var self = this;
            var payment_method_list = this.$el.find('.paymentmethod');
            // console.log('payment_method_list', payment_method_list)
            
            $.each(payment_method_list, function(idx, payment_method){
                const data_id = $(payment_method).data('id');
                const check_flag = self.check_t1c_flags(data_id);
                const is_t1cp = check_flag.is_t1cp;
                const is_t1ac = check_flag.is_t1ac;
                if (is_t1cp || is_t1ac) {
                    let the_card_no = self.pos.get_order().membercard.the_one_card_no
                    if (the_card_no === "N/A"){
                        $(payment_method).hide();
                        // console.log('hide', payment_method);
                    }
                    else{
                        // $(payment_method).show();
                        $(payment_method).hide();
                    }
                }
            });
        },
        render_the_one_card: function(){
            var self = this;
            var order = self.pos.get_order();
            var t1c_no = ''
            if(order.membercard.the_one_card_no != 'N/A'){
                t1c_no = order.membercard.the_one_card_no;
            }
            var TheOneCardScreenLabel = $(QWeb.render('TheOneCardScreenLabel', {the_one_card_no: t1c_no}));
            self.$('.theonecardpaymentscreen-container').html('');
            TheOneCardScreenLabel.appendTo(self.$('.theonecardpaymentscreen-container'));
        },
        renderElement: function () {
            this._super();
            this.render_the_one_card();
        },
        show: function () {
            this._super()
            this.render_the_one_card();
            this.hide_show_t1c();
        },
    });

});
