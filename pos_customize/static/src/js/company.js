odoo.define('pos_customize.company', function (require) {
    "use strict";

    var gui = require('point_of_sale.gui');
    var models = require('point_of_sale.models');
    var PosDB = require('point_of_sale.DB');
    var screens = require('point_of_sale.screens');
    var popups = require('point_of_sale.popups');
    var session = require('web.session');
    var core = require('web.core');
    var _t = core._t;
    var QWeb = core.qweb;



    models.load_models([
        {
            model: 'res.company',
            domain: function (self) {
                return [
                    ['id', '=', self.config.pos_company_id[0]],
                ];
            },
            loaded: function (self, company) {
                self.pos_company = company[0];
            },
        }
    ]);

    var _super_order = models.Order;
    models.Order = models.Order.extend({
        export_for_printing: function () {
            var pos_company = this.pos;
            var receipt = _super_order.prototype.export_for_printing.apply(this, arguments);

            receipt.company.pos_logo = pos_company.company_logo_base64;
            receipt.company.pos_company_name = pos_company.company.name;
            receipt.company.pos_tax_id = pos_company.company.vat;

            return receipt;
        },
        check_cash_limit: function () {

            if ((this.pos.pos_session.cash_register_balance_end < this.pos.config.cash_limit)
                || (this.pos.config.cash_limit == 0)){
                return true;
            }
            else{
                this.pos.gui.show_popup('alert', {
                    'title': 'Alert',
                    'body': 'Cash over limit. Please take money out.',
                });
                return false;
            }
        },
    });

    screens.ProductScreenWidget.include({
        show: function () {
            this._super();
            this.pos.get_order().check_cash_limit();
        },

        click_product: function(product) {
            if(this.pos.get_order().check_cash_limit()){
                if (product) {
                    if ( this.pos.config.product_ids.indexOf(product.id) != -1 ){
                        return true
                    }
                    if (product.is_hold_sale){
                        return true
                    } else if(product.to_weight && this.pos.config.iface_electronic_scale){
                        this.gui.show_screen('scale',{product: product});
                    }
                    else{
                        this.pos.get_order().add_product(product);
                    }
                }
            }
        },
    });
});

