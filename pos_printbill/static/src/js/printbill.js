odoo.define('pos_printbill.printbill', function (require) {
    "use strict";

    var core = require('web.core');
    var screens = require('point_of_sale.screens');
    var gui = require('point_of_sale.gui');
    var formats = require('web.formats');

    var QWeb = core.qweb;


    var BillScreenWidget = screens.ReceiptScreenWidget.extend({
        template: 'BillScreenWidget',
        click_next: function () {
            this.gui.show_screen('products');
        },
        click_back: function () {
            this.gui.show_screen('products');
        },
        render_receipt: function () {
            var order = this.pos.get_order();
            this.$('.pos-receipt-container').html(QWeb.render('PosBillTicket', {
                widget: this,
                order: order,
                receipt: order.export_for_printing(),
                orderlines: order.get_orderlines(),
                paymentlines: order.get_paymentlines(),
            }));
            this.$('.receipt-paymentlines').remove();
            this.$('.receipt-change').remove();
        },
        print_web: function () {
            window.print();
            this.gui.show_screen('products');
        },
    });

    gui.define_screen({name: 'bill', widget: BillScreenWidget});

    var PrintBillButton = screens.ActionButtonWidget.extend({
        template: 'PrintBillButton',
        print_xml: function () {
            var order = this.pos.get('selectedOrder');
            if (order.get_orderlines().length > 0) {
                var receipt = order.export_for_printing();
                receipt.bill = true;
                this.pos.proxy.print_receipt(QWeb.render('BillReceipt', {
                    receipt: receipt, widget: this, pos: this.pos, order: order,
                }));
            }
        },
        button_click: function () {
            var order = this.pos.get_order();
            var get_orderlines = order.get_orderlines();
            var product_ids = [];

            if (!this.pos.config.iface_print_via_proxy) {
                this.gui.show_screen('bill');
            } else {
                this.print_xml();
            }
        },
    });

    screens.define_action_button({
        'name': 'print_bill',
        'widget': PrintBillButton,
        'condition': function () {
            return true;
        },
    });





});
