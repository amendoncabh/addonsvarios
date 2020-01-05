odoo.define('pos_bill_on_payment.bill_on_payment', function (require) {
    "use strict";

    var core = require('web.core');
    var screens = require('point_of_sale.screens');
    var gui = require('point_of_sale.gui');
    var formats = require('web.formats');

    var QWeb = core.qweb;



    screens.PaymentScreenWidget.include({
        order_changes: function () {
            this._super();
            this.update_bill();
        },
        print_web: function () {
            window.print();
        },
        lock_screen: function (locked) {
            this._locked = locked;
        },
        print_xml: function () {
            var env = {
                widget: this,
                pos: this.pos,
                order: this.pos.get_order(),
                receipt: this.pos.get_order().export_for_printing(),
                paymentlines: this.pos.get_order().get_paymentlines()
            };
            var receipt = QWeb.render('XmlReceipt', env);

            this.pos.proxy.print_receipt(receipt);
        },
        print: function () {
            var self = this;
            if (!this.pos.config.iface_print_via_proxy) {
                // browser (html) printing
                this.lock_screen(true);
                setTimeout(function () {
                    self.lock_screen(false);
                }, 1000);
                this.print_web();
            } else {
                this.print_xml();
                this.lock_screen(false);
            }
        },
        renderElement: function () {
            var self = this;
            this._super();
            /*this.$('.button.print').click(function () {
                self.print();
            });*/
        },
        show: function () {


            this.lock_screen(false);

            this.update_bill();
            this._super();
        },
        customer_changed: function () {
            var self = this;
            this._super();
            this.pos.get_order().bind('changed_price', function () {
                self.update_bill();
                self.order_changes();
                self.render_paymentlines();
            });
        },
        update_bill: function () {
            var order = this.pos.get_order();

            var orderlines = order.get_orderlines();
 
            this.$('.pos-receipt-container').html(QWeb.render('PosTicket', {
                widget: this,
                order: order,
                receipt: order.export_for_printing(),
                orderlines: orderlines,
                paymentlines: order.get_paymentlines(),
            }));

            this.$('.receipt-paymentlines').remove();
            this.$('.receipt-change').remove();
        },
        reset_input: function(){
            var line = this.pos.get_order().selected_paymentline;
            this.firstinput  = true;
            if (line) {
                this.inputbuffer = this.format_currency_no_symbol(0.00);
            } else {
                this.inputbuffer = "";
            }
        },

    });




});
