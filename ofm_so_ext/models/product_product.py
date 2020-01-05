from odoo import models, api


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def get_product_detail(self):
        categ_id = self.env['product.category'].search([
            ('name', '=', 'All')
        ])

        uom_id = self.env['product.uom'].search([
            ('name', '=', 'Unit(s)')
        ])

        stock_route_ids = self.env['stock.location.route'].search([
            ('name', '=', 'Buy')
        ])

        route_ids = [(6, 0, stock_route_ids.ids)]

        return {
            'categ_id': categ_id.id,
            'uom_id': uom_id.id,
            'route_ids': route_ids,
        }

    def prepare_product_for_create(self, product_name, lst_price):
        product_detail = self.get_product_detail()

        product_deposit = {
            'name': product_name,
            'lst_price': lst_price,
            'list_price': lst_price,
            'sale_ok': True,
            'purchase_ok': True,
            'type': 'service',
            'categ_id': product_detail.get('categ_id', False),
            'uom_id': product_detail.get('uom_id', False),
            'route_ids': product_detail.get('route_ids', False),
            'brand_id': 1,
            'dept_ofm': 1,
            'taxes_id': False,
            'supplier_taxes_id': False,
        }

        return product_deposit

    @api.model
    def product_delivery_fee(self):
        product_sale = self.env['product.product'].search([
            ('name', '=', 'Delivery Fee')
        ])

        if not product_sale:
            deposit_product_sale = self.prepare_product_for_create(
                'Delivery Fee',
                0
            )

            self.create(deposit_product_sale)

    @api.model
    def product_delivery_fee_special(self):
        product_purchase = self.env['product.product'].search([
            ('name', '=', 'Delivery Fee Special')
        ])

        if not product_purchase:
            delivery_fee_special = self.env['ir.config_parameter'].search([
                ('key', '=', 'so_delivery_fee_special')
            ]).value

            deposit_product_purchase = self.prepare_product_for_create(
                'Delivery Fee Special',
                delivery_fee_special
            )

            self.create(deposit_product_purchase)
