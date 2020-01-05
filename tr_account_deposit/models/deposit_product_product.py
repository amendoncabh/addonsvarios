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

        vat_product = self.env['ir.config_parameter'].search([
            ('key', '=', 'vat_product')
        ]).value

        customer_taxes_ids = self.env['account.tax'].search([
            ('amount', '=', vat_product),
            ('type_tax_use', '=', 'sale')
        ])

        taxes_ids = [(6, 0, customer_taxes_ids.ids)]

        supplier_taxes_ids = self.env['account.tax'].search([
            ('amount', '=', vat_product),
            ('type_tax_use', '=', 'purchase')
        ])

        supplier_taxes_ids = [(6, 0, supplier_taxes_ids.ids)]

        return {
            'categ_id': categ_id.id,
            'uom_id': uom_id.id,
            'route_ids': route_ids,
            'taxes_ids': taxes_ids,
            'supplier_taxes_ids': supplier_taxes_ids,
        }

    def prepare_product_deposit_for_create(self, product_name, is_tax):
        product_detail = self.get_product_detail()

        product_deposit = {
            'name': product_name,
            'sale_ok': True,
            'purchase_ok': True,
            'type': 'service',
            'dept_ofm': 1,
            'categ_id': product_detail.get('categ_id', False),
            'uom_id': product_detail.get('uom_id', False),
            'route_ids': product_detail.get('route_ids', False),
            'brand_id': 1,
            'taxes_id': product_detail.get('taxes_ids', False) if is_tax else False,
            'supplier_taxes_id': product_detail.get('supplier_taxes_ids', False) if is_tax else False,
        }

        return product_deposit

    @api.model
    def deposit_product_from_sale(self):
        product_sale = self.env['product.product'].search([
            ('name', '=', 'Deposit From Sale')
        ])

        if not product_sale:
            deposit_product_sale = self.prepare_product_deposit_for_create('Deposit From Sale', True)

            self.create(deposit_product_sale)

    @api.model
    def deposit_product_from_sale_without_tax(self):
        product_sale = self.env['product.product'].search([
            ('name', '=', 'Deposit From Sale Without Tax')
        ])

        if not product_sale:
            deposit_product_sale = self.prepare_product_deposit_for_create('Deposit From Sale Without Tax', False)

            self.create(deposit_product_sale)

    @api.model
    def cash_credit_product_from_sale(self):
        product_sale = self.env['product.product'].search([
            ('name', '=', 'Cash/ Credit From Sale')
        ])

        if not product_sale:
            deposit_product_sale = self.prepare_product_deposit_for_create('Cash/ Credit From Sale', True)

            self.create(deposit_product_sale)

    @api.model
    def cash_credit_product_from_sale_without_tax(self):
        product_sale = self.env['product.product'].search([
            ('name', '=', 'Cash/ Credit From Sale Without Tax')
        ])

        if not product_sale:
            deposit_product_sale = self.prepare_product_deposit_for_create('Cash/ Credit From Sale Without Tax', False)

            self.create(deposit_product_sale)

    @api.model
    def deposit_product_from_purchase(self):
        product_purchase = self.env['product.product'].search([
            ('name', '=', 'Deposit From Purchase')
        ])

        if not product_purchase:
            deposit_product_purchase = self.prepare_product_deposit_for_create('Deposit From Purchase', True)

            self.create(deposit_product_purchase)

    @api.model
    def deposit_product_from_purchase_without_tax(self):
        product_purchase = self.env['product.product'].search([
            ('name', '=', 'Deposit From Purchase Without Tax')
        ])

        if not product_purchase:
            deposit_product_purchase = self.prepare_product_deposit_for_create('Deposit From Purchase Without Tax', False)

            self.create(deposit_product_purchase)
