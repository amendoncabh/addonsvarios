odoo.define('pos_discount_on_payment.discount_on_payment', function (require) {
    "use strict";

    var core = require('web.core');
    var screens = require('point_of_sale.screens');
    var gui = require('point_of_sale.gui');
    var formats = require('web.formats');
    var models = require('point_of_sale.models');
    var popup = require('point_of_sale.popups');
    var _t = require('web.core')._t;
    var utils = require('web.utils');

    var round_pr = utils.round_precision;
    var QWeb = core.qweb;

    models.load_fields('res.partner', 'vip');


    var NumberAndPercentPopupWidget = popup.extend({
        template: 'NumberAndPercentPopupWidget',
        show: function (options) {
            options = options || {};
            this._super(options);

            this.inputbuffer = '' + (options.value || '');
            this.decimal_separator = _t.database.parameters.decimal_point;
            this.renderElement();
            this.firstinput = true;
        },
        click_numpad: function (event) {
            var is_percent = false;
            if (this.inputbuffer.indexOf('%') >= 0) {
                is_percent = true;
                this.inputbuffer = this.inputbuffer.replace('%', '');
                this.$('.value').text(this.inputbuffer);
                if ($(event.target).data('action') == 'BACKSPACE') {
                    $('.percent-button').removeClass('highlight');
                    return;
                }
            }

            var newbuf = this.gui.numpad_input(
                    this.inputbuffer,
                    $(event.target).data('action'),
                    {'firstinput': this.firstinput});

            this.firstinput = (newbuf.length === 0);

            if (newbuf !== this.inputbuffer) {
                if (is_percent) {
                    newbuf += '%';
                }
                this.inputbuffer = newbuf;
                this.$('.value').text(this.inputbuffer);
            }
        },
        click_item: function (event) {
            var action = $(event.target).data('action');

            if ($(event.target).hasClass('highlight')) {
                $(event.target).removeClass('highlight');
                if (this.inputbuffer.indexOf('%') >= 0) {
                    this.inputbuffer = this.inputbuffer.replace('%', '');
                    this.$('.value').text(this.inputbuffer);
                }

            } else {
                $(event.target).addClass('highlight');
                this.inputbuffer += action;
                this.$('.value').text(this.inputbuffer);
            }


        },
        click_confirm: function () {
            this.gui.close_popup();
            if (this.options.confirm) {
                this.options.confirm.call(this, this.inputbuffer);
            }
        }
    });
    gui.define_popup({name: 'number_and_percent', widget: NumberAndPercentPopupWidget});


    models.Order = models.Order.extend({
        set_vip_discount: function (discount) {
            discount = -(discount);
            var discount_product = this.pos.db.get_product_by_id(this.pos.config.vip_discount_product_id[0]);
            var lines = this.get_orderlines();
            if (discount_product) {
                for (var i = 0; i < lines.length; i++) {
                    if (lines[i].get_product() === discount_product) {
                        lines[i].set_unit_price(discount);
                        return;
                    }
                }
                this.add_product(discount_product, {quantity: 1, price: discount, extras: {vip_discount: true}});
            }
        },
        get_total_with_tax_no_discount: function () {
            return this.get_total_without_tax_no_discount() + this.get_total_tax();
        },
        get_total_without_tax_no_discount: function () {
            return round_pr(this.orderlines.reduce((function (sum, orderLine) {
                if (orderLine.vip_discount) {
                    return sum;
                }
                return sum + orderLine.get_price_without_tax();
            }), 0), this.pos.currency.rounding);
        },
    });
    screens.PaymentScreenWidget.include({
        show_vip_discount: function () {
            var client = this.pos.get_client();

            if (client && client.vip == "yes") {
                this.$('.js_discount').show();
            } else {
                this.$('.js_discount').hide();
            }
        },
        customer_changed: function () {
            this._super();
            this.show_vip_discount();
        },
        discount: function () {
            var self = this;
            var order = this.pos.get_order();
            var total = order.get_total_with_tax_no_discount();
//            lines[0].set_discount(50);
//            self.order_changes();
//            self.render_paymentlines();


            this.gui.show_popup('number_and_percent', {
                'title': 'Discount',
                'value': self.format_currency_no_symbol(0),
                'confirm': function (value) {
                    var found_percent = value.toString().indexOf("%");
                    if (found_percent >= 0) {
                        // found %
                        value = parseFloat(value.toString().replace('%', ''));
                        value = total * (value / 100);
                        value = (value).toFixed()
                        value = value.toString();

                    }
                    order.set_vip_discount(formats.parse_value(value, {type: "float"}, 0));
                    self.order_changes();
                    self.render_paymentlines();
                }
            });

        },
        renderElement: function () {
            var self = this;
            this._super();
            this.$('.back').click(function () {
                var order = self.pos.get_order();
                var lines = order.get_orderlines();
//                $.each(lines, function (i, e) {
//                    if (this.pos.config.vip_discount_product_id[0] == lines[i].product.id) {
//                        // found vip product must remove
//                        order.remove_orderline(lines[i]);
//                    }
//
//                });

            });
            this.$('.js_discount').click(function () {
                self.discount();
            });
            this.show_vip_discount();


        },
    });
});
