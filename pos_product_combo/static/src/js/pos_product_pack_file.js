odoo.define('pos_product_combo.pos_product_pack_file', function (require) {
"use strict";
var screens = require('point_of_sale.screens');
var models = require('point_of_sale.models');
var PopUpWidget=require('point_of_sale.popups');
var gui = require('point_of_sale.gui');
var _t  = require('web.core')._t;
var Model = require('web.DataModel');
var core = require('web.core');
var QWeb = core.qweb;
var utils = require('web.utils');
var round_di = utils.round_decimals;

var modelss = models.PosModel.prototype.models;
for(var i=0; i<modelss.length; i++){
    var model=modelss[i];
    if(model.model === 'product.product'){
        model.fields.push('is_pack');
        model.fields.push('qty_available');
    } 
}

models.load_models([
//    {
//        model: 'product.product',
//        fields: ['id','name', 'product_pack_id', 'lst_price', 'is_pack'],
//        domain: function(self){ return [['is_pack', '=',true]]; },
//        loaded: function(self,result){
//            console.log('selff',self)
//            self.set({'product_pack': result});
//        },
//    },
    {
        model: 'product.pack',
        condition: function(self){ return true; },
        fields: ['id','product_id','product_quantity','uom_id','price','name'],
        domain: function(self){ return []; },
        loaded: function(self,result){
            self.set({'pack_product': result});
        },
    }],{'after': 'product.product'});

var _super = models.Orderline;
models.Orderline = models.Orderline.extend({
    getPackProduct:function(pack_product_id,product_price,product_qty){
        var self = this;
        pack_product_id = self.product.id
        var pack_product=self.pos.get('product_pack');
        var pack_products=self.pos.get('pack_product');
        var pack_product_list=[];
        var savedprice=0;
        for(var i=0;i<pack_product.length;i++)
        {   
            if(pack_product[i].id==pack_product_id && self.product.is_pack && (pack_product[i].product_pack_id).length>0 )
            {
                for(var j=0;j<(pack_product[i].product_pack_id).length;j++){ 

                    for(var k=0;k<pack_products.length;k++){
                        if(pack_products[k].id==pack_product[i].product_pack_id[j]){
                        var product_val={'display_name':pack_products[k].product_id[1],'uom_id':pack_products[k].uom_id,'price':pack_products[k].price};
                        pack_product_list.push({'product':product_val,'qty':pack_products[k].product_quantity});
                        }
                    }
                }
                return {'pack_product_list':pack_product_list};
            }
        }         
    },
});
});
