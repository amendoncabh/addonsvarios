odoo.define('ofm_the_one_card.t1cc_cash_coupon', function (require) {
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

    var CashCouponPopupWidget = popups.extend({
        template: 'CashCouponPopupWidget',

        check_duplicate: async function (barcode) {
            var self = this;
            var deferred = $.Deferred();
            const barcode_list = [barcode];
            var proceed = true;

            //check on payment screen
            const paymentlines = self.pos.get_order().paymentlines.models;
            $.each(paymentlines, function(index, line){
                if (line.t1cc_barcode == barcode) {
                    proceed = false;
                }
            });
            //check on previous orders
            await new Model("account.bank.statement.line").call("check_duplicate_t1cc", barcode_list).then(function(result){
                if (result) {
                    proceed = false;
                }    
            });

            return proceed;
        },

        click_confirm: function(){
            var self = this;
            let barcode = $('#cash-coupon-barcode').val();
            let amount = $('#cash-coupon-amount').val();
            if (barcode && amount) {
                if (barcode.length <= 255) {
                    self.check_duplicate(barcode).then(function(proceed){
                        if (proceed) {           
                            if (self.options.confirm) {
                                self.options.confirm.call(self);
                            }
                        }else{
                            $('#alert').html('Barcode with serial [' + barcode + '] has been previously used.');
                        }
                    });
                }else{
                    $('#alert').html('ข้อมูลที่ระบุมีจำนวนตัวอักษรมากกว่า 255 ตัว กรุณาตรวจสอบใหม่อีกครั้ง');            
                }
            }
            else if (barcode && !amount) {
                $('#cash-coupon-amount').css({ "border": '#FF0000 1px solid'});

            }
            else if (!barcode && amount) {
                $('#cash-coupon-barcode').css({ "border": '#FF0000 1px solid'});
            }
            else {
                $('#cash-coupon-amount').css({ "border": '#FF0000 1px solid'});
                $('#cash-coupon-barcode').css({ "border": '#FF0000 1px solid'});
            }
        },

        init_behavior: function() {
            var input_field = this.$('#cash-coupon-barcode');
            input_field.focus();
        },

        show: function(options) {
            var self = this;
            this._super(options);   
            self.init_behavior();
        },
    });
    gui.define_popup({name: 'cash_coupon_popup', widget: CashCouponPopupWidget});
});