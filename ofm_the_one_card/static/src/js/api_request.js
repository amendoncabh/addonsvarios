odoo.define('ofm_the_one_card.api_request', function (require) {
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

    var ApiWidget = popups.extend({

        zero_pad: function(num,size){
            var s = ""+num;
            while (s.length < size) {
                s = "0" + s;
            }
            return s;
        },

        get_request_header: function(date){
            var self = this;
            var now = moment(date);
            /*<PartnerCode>_<storecode>_<Receipt-no>_#request_DD_HHMMSSMMM*/
            var SourceTransID = [
                'OFM',
                self.pos.branch.branch_code,
                self.pos.get_order().get_inv_no(),
                self.zero_pad(++self.pos.request_the_one_card_no, 3),
                now.format('DD_HH:mm:ss:SSS')
            ].join('_');
            var i;
            return {
                'SourceTransID': SourceTransID,
                'RequestTime': now.format('DDMMYYYY_HH:mm:ss:SSS'),
                'LanguagePreference': 'TH',
                'client_id': self.pos.the_1_config.client_id,
                'client_secret': self.pos.the_1_config.client_secret,
                'PartnerCode': self.pos.the_1_config.partnerCode,
                'TransactionChannel': self.pos.the_1_config.transactionChannel,
                'Content-Type': 'application/json',
            }
        },

        handle_error: function(error) {
            self.chrome.loading_hide();
            console.log(error);
            if (error.responseJSON){
                if (error.responseJSON.error){
                    self.gui.show_popup('my_message',{
                        'title': _t('Warning'),
                        'body': _t(error.responseJSON.error),
                    });
                } else {
                    self.gui.show_popup('my_message',{
                        'title': _t('Warning'),
                        'body': _t(error.responseJSON.displayErrorMessage),
                    });
                }
            } else {
                self.gui.show_popup('my_message',{
                    'title': _t(error.statusText),
                    'body': _t(error.responseText),
                });
            }
        },

        make_request: function(endpoint, method, header, body, success_callback) {
            var self = this;
            
            $.ajax({
                url: endpoint,
                type: method,
                data: JSON.stringify(body),
                contentType: 'application/json',
                secure: true,
                headers: header,
                dataType: 'json',
                success: success_callback,
                error: self.handle_error,
            });
        },

    });
    gui.define_popup({name:'api_widget', widget: ApiWidget});

    return {
        ApiWidget: ApiWidget,
    };

});