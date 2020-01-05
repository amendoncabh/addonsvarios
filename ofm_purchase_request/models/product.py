from odoo import models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def get_where_product_template(self):
        query_where_product = super(ProductProduct, self).get_where_product_template()
        search_model = self.env.context.get('search_model', False)

        if search_model in self.get_search_model_include_prod_status():
            prs_product_status = self.env['ir.config_parameter'].search([
                ('key', '=', 'prs_product_status')
            ]).value

            if prs_product_status:
                prs_product_status = prs_product_status.split(',')
                prs_product_status = ','.join('\'{0}\''.format(status) for status in prs_product_status)
                query_where_product = """
                    and prod_status in (%s)
                """ % prs_product_status

        return query_where_product