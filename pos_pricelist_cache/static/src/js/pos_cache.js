odoo.define('pos_pricelist_cache.pos_cache', function (require) {
    "use strict";
    var core = require('web.core');
    var models = require('point_of_sale.models');
    var Model = require('web.DataModel');
    var PosDB = require('point_of_sale.DB');
    var screens = require('point_of_sale.screens');
    var chrome = require('point_of_sale.chrome');
    var _t = core._t;


    PosDB.include({
        add_products: function (products, filter_template=false) {
            var self = this;
            if(filter_template && self.template_product_ids && self.template_product_ids instanceof Array && self.template_product_ids.length > 0){
                products = products.filter((product)=> self.template_product_ids.includes(product.id));
            }
            this._super(products);
        },
    });

    var posmodel_super = models.PosModel.prototype;
    models.PosModel = models.PosModel.extend({
        load_server_data: function () {
            var self = this;

            var product_index = _.findIndex(this.models, function (model) {
                return model.model === "product.product";
            });

            // Give both the fields and domain to pos_cache in the
            // backend. This way we don't have to hardcode these
            // values in the backend and they automatically stay in
            // sync with whatever is defined (and maybe extended by
            // other modules) in js.
            var product_model = this.models[product_index];
            var product_fields = product_model.fields;
            var product_domain = product_model.domain;

            // We don't want to load product.product the normal
            // uncached way, so get rid of it.
            if (product_index !== -1) {
                this.models.splice(product_index, 1);
            }

            return posmodel_super.load_server_data.apply(this, arguments).then(function () {
                var records = new Model('product.pricelist').call('get_products_from_cache',
                                                           [self.config.pricelist_id[0]]);

                self.chrome.loading_message(_t('Loading') + ' product.product', 1);
                return records.then(function (products) {
                    self.db.products = products;
                    self.db.add_products(products, true);
                    var products_pack = [];
                    $.each(products, function (i, product) {
                        if (product.is_pack) {
                            products_pack.push(product);
                        }
                    });
                    self.set({'product_pack': products_pack});

                    self.models.push(product_model);
                });
            });
        },
        sync_product_detail_delay: 2000,
        sync_product_detail: {
            next_interval: false,
            next_interval_datetime: false,
        },
        set_next_interval: function(datetime){
            if(!datetime)
                return;
            var self = this;
            if(!datetime.includes("Z"))
                datetime += "Z"
            datetime = new Date(datetime);
            if(self.sync_product_detail.next_interval || self.sync_product_detail.next_interval_datetime){
                clearTimeout(self.sync_product_detail.next_interval);
                self.sync_product_detail.next_interval_datetime = false;
            }

            var seconds = datetime - new Date() + self.sync_product_detail_delay;
            // check is greater than date convert from milli-sec to date 3600*24*1000
            if(Math.floor(seconds / (86400000)) > 1){
                return
            }

            self.sync_product_detail.next_interval = setTimeout(function(){
                self.call_update_product_detail();
                self.sync_product_detail.next_interval_datetime = false;
            }, seconds);

            self.sync_product_detail.next_interval_datetime = datetime;
        },
        call_update_product_detail: function(){
            var self = this;
            if(self.get('product_sync_status') == 'connecting'){
                return $.Deferred().reject();
            }

            var deferred = $.Deferred();
            new Model("product.product").call( "inquiry_product_detail", [{
                product_ids: self.db.template_product_ids,
                branch_id: self.branch.id,
            }], undefined, {shadow: true}).then(function(result) {
                var products = result.products;
                if(products && products instanceof Array && products.length) {
                    var flag_refresh_cache = (self.gui.screen_instances && self.gui.screen_instances.products
                        && self.gui.screen_instances.products.product_list_widget
                        && self.gui.screen_instances.products.product_list_widget.product_cache);

                    products.forEach(function(product){
                        var product_db = self.db.product_by_id[product.id];
                        if(product_db){
                            product_db.price = product.price;
                            product_db.list_price = product.price;
                            product_db.lst_price = product.price;
                            product_db.lst_price = product.price;
                            if(product.taxes_id && product.taxes_id.length)
                                product_db.taxes_id = product.taxes_id;
                            else
                                product_db.taxes_id = [];
                            if(product.prod_status)
                                product_db.prod_status = product.prod_status;
                            else
                                product_db.prod_status = false;
                        }
                        if(flag_refresh_cache){
                            self.gui.screen_instances.products.product_list_widget.product_cache.clear_node(product.id);
                        }
                    });
                    if(flag_refresh_cache){
                        self.gui.screen_instances.products.product_list_widget.renderElement();
                    }
                }
                if(result.next_interval)
                    self.set_next_interval(result.next_interval);
                self.set('product_sync_status', 'connected');
                deferred.resolve();
            }, function(unused, e) {
                // no error popup if request is interrupted or fails for any reason
                e.preventDefault();
                self.set('product_sync_status', 'disconnected');
                deferred.resolve();
            });
            self.set('product_sync_status', 'connecting');
            return deferred;
        },
        after_load_server_data: function(){
            var self = this;
            return this.call_update_product_detail().then(function(){
                return posmodel_super.after_load_server_data.apply(self);
            });
        },
    });


    var SyncProductDetailWidget = chrome.StatusWidget.extend({
        template: 'SyncProductDetailWidget',
        start: function(){
            var self = this;
            this.set_status(this.pos.get('product_sync_status'));

            this.pos.bind('change:product_sync_status', function(pos, status){
                self.set_status(status);
            });
            this.$el.click(function(){
                self.pos.call_update_product_detail();
            });
        },
    });

    var chrome_prototype = chrome.Chrome.prototype;
    chrome.Chrome = chrome.Chrome.extend({
        // add to the first index
        widget: chrome_prototype.widgets.unshift({
            'name':   'sync_product_detail',
            'widget': SyncProductDetailWidget,
            'append':  '.pos-rightheader',
            'condition': function(){ return true;},
        })
    });

    return {
        SyncProductDetailWidget: SyncProductDetailWidget,
    }
});
