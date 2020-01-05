# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class WizardMultiChartsAccounts(models.TransientModel):
    _inherit = 'wizard.multi.charts.accounts'

    def get_vat_product_by_company(self, company_id):
        vat_product = self.env['ir.config_parameter'].search([
            ('key', '=', 'vat_product')
        ])

        if not vat_product:
            vat_product = 7
        else:
            vat_product = vat_product.value

        account_tax = self.env['account.tax']

        vat_in = account_tax.search([
            ('company_id', '=', company_id.id),
            ('type_tax_use', '=', 'purchase'),
            ('amount', '=', vat_product)
        ])
        vat_out = account_tax.search([
            ('company_id', '=', company_id.id),
            ('type_tax_use', '=', 'sale'),
            ('amount', '=', vat_product)
        ])

        return {
            'vat_in': vat_in,
            'vat_out': vat_out
        }

    def add_vat_to_products(self, company_id):
        if not self.company_id or not company_id:
            return False
        if not company_id:
            company_id = self.company_id

        vat = self.get_vat_product_by_company(company_id)

        query_str = """
            INSERT INTO product_taxes_rel (prod_id, tax_id)
            SELECT prod_id, %s::int as tax_id FROM product_taxes_rel
            WHERE tax_id != %s::int group by prod_id
        """ % (vat['vat_out'].id, vat['vat_out'].id,)

        self.env.cr.execute(query_str)

        query_str2 = """
            INSERT INTO product_supplier_taxes_rel (prod_id, tax_id)
            SELECT prod_id, %s::int as tax_id from product_supplier_taxes_rel
            WHERE tax_id != %s::int group by prod_id
        """ % (vat['vat_in'].id, vat['vat_in'].id,)

        self.env.cr.execute(query_str2)
        self.env.cr.commit()

    @api.multi
    def execute(self):
        res = super(WizardMultiChartsAccounts, self).execute()
        if self.company_id:
            self.add_vat_to_products(self.company_id)
        return res
