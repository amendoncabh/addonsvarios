odoo.define('pos_no_change.no_change', function (require) {
    "use strict";

    var core = require('web.core');
    var screens = require('point_of_sale.screens');
    var gui = require('point_of_sale.gui');
    var formats = require('web.formats');
    var models = require('point_of_sale.models');
    var SuperOrder = models.Order;
    var utils = require('web.utils');
    var round_pr = utils.round_precision;

    var QWeb = core.qweb;

    screens.PaymentScreenWidget.include({
        set_no_change: function() {
            var self = this;
            var open_paymentline = false;
            var order = this.pos.get_order();
            var lines = order.get_orderlines();
            var total = order.get_total_with_tax();
            var payment_lines = order.get_paymentlines();
            if (payment_lines.length == 0) {
                open_paymentline = true;
            }
            if (open_paymentline) {
                order.add_paymentline( self.pos.cashregisters[0]);
                self.render_paymentlines();
            }
            if (order.selected_paymentline) {
                var due = order.get_due(order.selected_paymentline);
                if(order.selected_paymentline.cashregister.journal.type == 'cash'){
                    var amount_total_rounding = order.get_total_rounding(due);
                    if(amount_total_rounding != due){
                        order.change_rounding = round_pr(Math.abs(due - amount_total_rounding), 0.01);
                        due = due - order.change_rounding;
                    }
                }
                else{
                    if(!order.is_paid_with_cash()){
                        order.change_rounding = 0.0;
                    }
                }
                order.selected_paymentline.set_amount(due);
                self.order_changes();
                self.render_paymentlines();
                self.$('.paymentline.selected .edit').text(this.format_currency_no_symbol(due));
            };
            return;
        },
        payment_input: function(input) {
			var self = this;
			self._super(input);
            var payment_type = this.pos.get_order().get_paymentlines();

            for (var payment in payment_type){
                if(payment_type[payment].selected){
                    if (!payment_type[payment].cashregister.journal.flag_change){
                        if (Number(this.inputbuffer.replace(',', '')) > this.pos.get_order().get_due(payment_type[payment])){
                            self.set_no_change();
                        }
                    }
                    break;
                }
            }
		},
        renderElement: function () {
            var self = this;
            this._super();
            this.$('.js_set_no_change').click(function(){
                self.set_no_change();
            });
        },
    });
});
