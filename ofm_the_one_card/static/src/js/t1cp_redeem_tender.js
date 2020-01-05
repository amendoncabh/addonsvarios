odoo.define('ofm_the_one_card.t1cp_redeem_tender', function (require) {
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

    var CancelRedeemTenderFailPopupWidget = popups.extend({
        template: 'CancelRedeemTenderFailPopupWidget',
    });
    gui.define_popup({name: 'cancel_redeem_tender_fail', widget: CancelRedeemTenderFailPopupWidget});

    var SuperPosModel = models.PosModel.prototype;
    models.PosModel = models.PosModel.extend({
        initialize: function (session, attributes) {
            SuperPosModel.initialize.call(this, session, attributes);
            this.request_the_one_card_no = 0;
        },

        cancel_batch_t1cp: function (return_dict) {
            var self = this;
            new Model("pos.order").call("cancel_batch_t1cp", return_dict).then(function(result){
                var result_obj = JSON.parse(result);
                console.log(result_obj);
                if (result_obj.failed.length) {
                    self.gui.show_popup('cancel_redeem_tender_fail', {
                        'title': 'Cancel Failure',
                        'body': "Receipt numbers with cancel failures: " + result_obj.failed.join(','),
                        confirm: function() {
                            // console.log(self.cancel_batch_t1cp);
                            self.cancel_batch_t1cp(return_dict);
                            this.gui.close_popup();
                        },
                    });
                }
            });
        },

		_save_to_server: function (orders, options) {
            var self = this;
			return SuperPosModel._save_to_server.call(this,orders,options).then(function(return_dict){
                //Cancelling redeem tender lines
                //if the return dict of order_ids is not empty then we should use those ids to do an api request to
                //cancel those lines using the tr_call_api model
                var order = self.get_order();
                if (order){
                    const is_void = order.is_void_order;
                    const is_return = order.is_return_order;
                    if (return_dict.length && (is_void || is_return)) {
                        self.cancel_batch_t1cp(return_dict)
                    }
                }
                return return_dict.order_ids;
            });
		},
    });

    var PointTemplatePopupWidget = popups.extend({
        template:"PointTemplatePopupWidget",

		events: {
            'click .button.confirm': 'proceed_to_redeem',
            'click .button.cancel':  'click_cancel',
        },
        get_totals: function(){
            var point_redeem_lines = $('.return_popup_tr');
            // console.log(point_redeem_lines);
            point_redeem_lines = point_redeem_lines.slice(2);
            var point_total = 0;
            var amount_total = 0;
            $.each(point_redeem_lines, function(idx, line){
                let is_checked = $(line).find('input:checked');
                if (is_checked.length > 0) {
                    point_total += parseInt($(line).attr('points'));
                    amount_total += parseInt($(line).attr('amount'));
                }
            });
            return {'point_total' : point_total, 'amount_total' : amount_total};
        },
        in_process: false, //set and unset in redeem function. This is used to prevent user from double-clicking
        proceed_to_redeem: function(event){
            var self = this;
            // checks if in process, else run redeem
            if (self.in_process) {
                return;
            } else {
                self.redeem(event);
            }
        },
        redeem: function(event){
            var self = this;
            const data_id = self.options.data_id;
            self.in_process = true;
            const totals= self.get_totals();
            const point_total = totals.point_total;
            const amount_total = totals.amount_total;
            //order information
            var order = self.pos.get_order();
            const branch = self.pos.branch;
            const receipt_no = order.get_inv_no();
            const pos_no = self.pos.config.pos_no;
            const store_no = "SOFC" + branch.branch_code;
            const verification_txn_id = order.verify_targettransid;
            //member info
            const member_info = order.membercard;
            var phone_no = member_info.phone.replace || '';
            const card_no = member_info.the_one_card_no || ''; 
            const national_id = '';
            //if card number is set then set phone number to empty string
            (card_no) ? phone_no = '' : phone_no = phone_no;
            // setting product items
            var product_items = [
                {
                    "product": "SBL-RDM-TENDER",
                    "redeemPoint": point_total,
                    "referenceCode": "T1CP",
                }
            ];
                
            //t1c info
            const t1c_config = self.pos.the_1_config;
            const t1c_url = t1c_config.T1CRedeemTenderSrv.url;
            const method = t1c_config.T1CRedeemTenderSrv.method;
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
                "verificationTxnID": verification_txn_id,
            }

            // console.log(header);

            var redeem_success = function(data, status, xhr) {
                self.chrome.loading_hide();
                const body = JSON.parse(data.body);
                const ISC_firstchar = body.integrationStatusCode.charAt(0);
                const display_error = body.displayErrorMessage;
                if (ISC_firstchar === "0") {
                    const response_header = data.headers;
                    const response_body = body.responseBody;
                    console.log(response_body);
                    // order.redeem_tender_targettransid = response_header.targettransid;
                    order.membercard.balance_points = response_body.pointsAfter;
                    // order.siebelRedeemReceiptNo = response_body.siebelRedeemReceiptNo;
                    var cashregister = null;
                    for ( var i = 0; i < self.pos.cashregisters.length; i++ ) {
                        if ( self.pos.cashregisters[i].journal_id[0] === data_id ){
                            cashregister = self.pos.cashregisters[i];
                            break;
                        }
                    }
                    let options = {
                        "code" : response_body.siebelRedeemReceiptNo,
                        "amount" : amount_total,
                        "transactions": response_body.transactions,
                    };
                    order.add_t1c_line(cashregister, options);
                    order.pos.gui.screen_instances.payment.render_paymentlines()
                    self.click_cancel();
                }
                else {
                    self.gui.show_popup('my_message',{
                        'title': _t('Warning'),
                        'body': _t(display_error),
                    });                         
                }
                self.in_process = false;
            }

            //enter loading_screen
            self.chrome.loading_show();
            self.chrome.loading_message('กำลังประมวลผล', 0.8);
            self.gui.popup_instances.api_widget.make_request(self.pos.cors_proxy, method, _.extend(header,{'Target-URL': t1c_url}), body, redeem_success);
        },
    });
    gui.define_popup({name: 'point_template_popup', widget: PointTemplatePopupWidget});

});
