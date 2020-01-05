odoo.define('pos_stock_display.stock_display', function (require) {
    "use strict";
    var models = require('point_of_sale.models');

    var screens = require('point_of_sale.screens');
    var core = require('web.core');
    var utils = require('web.utils');

    var round_pr = utils.round_precision;
    var QWeb = core.qweb;

    var exports = models;
    
//    models.load_fields = function (model_name, fields) {
//        if (!(fields instanceof Array)) {
//            fields = [fields];
//        }
//        
//        var models = exports.PosModel.prototype.models;
//        for (var i = 0; i < models.length; i++) {
//            var model = models[i];
//            if (model.model === model_name) {
//                // if 'fields' is empty all fields are loaded, so we do not need
//                // to modify the array
//                if ((model.fields instanceof Array) && model.fields.length > 0) {
//                    model.fields = model.fields.concat(fields || []);
//                }
//            }
//        }
//    };
    models.load_fields('product.product', 'qty_available');

});