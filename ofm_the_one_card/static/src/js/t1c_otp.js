odoo.define('ofm_the_one_card.t1c_otp', function (require) {
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

    var OtpPopupWidget = popups.extend({
        template:"OtpPopupWidget",

        events: {
            'click .button.confirm': 'click_confirm',
            'click .button.cancel':  'click_cancel',
            'click .button.resend': 'click_resend',
        },
        init_behavior: function() {
            var input_field = this.$('#otp_code');
            input_field.focus();
        },
        zero_pad: function(num,size){
            var s = ""+num;
            while (s.length < size) {
                s = "0" + s;
            }
            return s;
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
            // console.log(latest_point_template);
            self.gui.show_popup('point_template_popup', {
                'title': _t('Redeem Points (' + latest_point_template.name + ')'),
                'lines': latest_point_template_lines,
                'data_id': data_id,
            });       
        },
        otp_verify: function(reference_text, code, system_id) {
            if ($('#otp_code').val()) {
                var self = this;
                const data_id = self.options.data_id;
                self.chrome.loading_show();
                //order information
                var order = self.pos.get_order();
                //otp info
                const otp_ref_text = reference_text;
                const otp_code = code;
                const otp_sys_id = system_id;
                //t1c info
                const t1c_config = self.pos.the_1_config;
                const t1c_url = t1c_config.BSVfyOTPSrv.url;
                const method = t1c_config.BSVfyOTPSrv.method;
                const header = self.gui.popup_instances.api_widget.get_request_header(new Date());
                const body = {
                    "otpRefText": otp_ref_text,
                    "otpCode": otp_code,
                    "otpSysID": otp_sys_id,
                };

                self.chrome.loading_message('กำลังประมวลผล', 0.8);

                var otp_verify_success = function(data, status, xhr) {
                    self.chrome.loading_hide();
                    const ISC_firstchar = data.integrationStatusCode.charAt(0);
                    const display_error = data.displayErrorMessage;
                    //open point redeem popup since OTP codes matched
                    if (ISC_firstchar === "0") {
                        order.otp_verified = true;
                        self.display_point_redeem(data_id);
                    }
                    //seibel server side issue
                    else if (ISC_firstchar === "1"){
                        $('#status').html(display_error + ". Please wait and try again.");
                    }
                    else {
                        $('#otp_code').val('');
                        // Case: OTP has expired
                        if (display_error.includes("EXPIRE")) {
                            $('#status').html('OTP has expired. Please resend OTP.');
                            $('#otp_code').prop("disabled", true);
                            $('.button.confirm').prop("disabled", true);
                        }
                        // Case: Incorrect OTP  code
                        else { 
                            $('#status').html(display_error);
                            let no_tries = parseInt($('#no_tries').text());
                            no_tries += 1;
                            $('#no_tries').html(no_tries);
                            if (no_tries >= 3) {
                                $('#otp_code').prop("disabled", true);
                                $('.button.confirm').prop("disabled", true);
                                $('#status').html('Max number of tries exceeded. Please resend OTP.');
                            }
                        }
                    }
                };
                self.gui.popup_instances.api_widget.make_request(t1c_url, method, header, body, otp_verify_success);
            }
        },
        otp_request: function(data_id) {
            var self = this;
            self.chrome.loading_show();
            //order information
            var order = self.pos.get_order();
            //member info
            const member_info = order.membercard;
            // var phone_no = "0955153792";
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

            self.chrome.loading_message('กำลังประมวลผล', 0.8);

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
                    $('#otp_ref_text').html(response_body.otpRefText);
                    $('#otp_code').prop("disabled", false);
                    $('.button.confirm').prop("disabled", false);
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
        click_confirm: function(){
            const self = this;
            const order = self.pos.get_order();
            const otp_ref_text = order.otp.otpRefText;
            const code_input = $('#otp_code').val();
            const otp_trans_id = order.otp.OTPSysID;
            self.otp_verify(otp_ref_text, code_input, otp_trans_id);
        },
        click_resend: function(){
            self = this;
            self.otp_request();
            $('#status').html("OTP code resent. Try again");
            $('#no_tries').html(0);
            $('#otp_code').val("");
        },
        show: function(options) {
            var self = this;
            this._super(options);   
            self.init_behavior();
        },
    });
    gui.define_popup({name: 'otp_popup', widget: OtpPopupWidget});

});
