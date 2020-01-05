odoo.define('ofm_the_one_card.t1ac_ecash_coupon', function (require) {
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

    var E_CashCouponPopupWidget = popups.extend({
        template: 'E_CashCouponPopupWidget',

        events: {
            'click .button.confirm': 'click_confirm',
            'click .button.cancel': 'click_cancel',
        },

        init_behavior: function() {
            var self = this;
            var input_field = this.$('#e-cash-coupon-barcode');
            input_field.focus();
            input_field.on('keypress', function(e){
                let keycode = (e.keyCode ? e.keyCode : e.which);
                if (keycode == '13'){
                    self.click_confirm();
                }
            });
        },

        click_confirm: function(){
            var self = this;            
            const barcode = $('#e-cash-coupon-barcode').val();
            const input_field = $('#e-cash-coupon-barcode');
            if (input_field.val().length) {
                self.query_coupon(barcode);
            }else{
                self.query_coupon(barcode);
            }
        },
        
        show: function(options) {
            var self = this;
            self.chrome.loading_hide();
            this._super(options);   
            self.init_behavior();
        },

        query_coupon: function(barcode) {
            var self = this;
            console.log("querying voucher: " + barcode);
            self.chrome.loading_show();
            self.chrome.loading_message('กำลังประมวลผล', 0.8);
            //order information
            var order = self.pos.get_order();
            //member info
            const member_info = order.membercard;
            const card_no = member_info.the_one_card_no;
            //t1c info
            const t1c_config = self.pos.the_1_config;
            const t1c_url = "https://uat-api.central.co.th/t1c/voucher/Redemption/1_0";
            const method = "POST";
            const header = self.gui.popup_instances.api_widget.get_request_header(new Date());
            const body = {
                "cardNo": card_no,
                "voucherNo": barcode.trim(),
                "pageNumber": 1,
            };

            var voucher_request_success = function(data, status, xhr) {
                self.chrome.loading_hide();
                console.log(data);
            }
            
            self.gui.popup_instances.api_widget.make_request(t1c_url, method, header, body, voucher_request_success);
        }
    });
    gui.define_popup({name: 'e_cash_coupon_popup', widget: E_CashCouponPopupWidget});

    // var VoucherPopupWidget = popups.extend({
    //     template: 'VoucherPopupWidget',

    //     events: {
    //         // 'click #web_scanner': 'open_scanner',
    //         'click .button.confirm': 'click_confirm',
    //         'click .button.cancel': 'click_cancel',
    //     },

    //     click_confirm: function(){
    //         console.log('clicked confirm')
    //     },
        
    //     show: function(options) {
    //         var self = this;
    //         self._super(options);
    //     },

    // });
    // gui.define_popup({name: 'voucher_popup', widget: VoucherPopupWidget});

});
