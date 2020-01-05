# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

__author__ = 'Pajaree'


class ProductNotSaleReport(models.TransientModel):
    _name = 'product.not.sale.report.wizard'
    _description = "Product Not Sales Report"

    start_date = fields.Date(
        string='Start Date',
        default=fields.Datetime.now,
    )
    end_date = fields.Date(
        string='End Date',
        default=fields.Datetime.now,
    )
    branch_id = fields.Many2one(
        'pos.branch',
        string='Branch'
    )
    jasper_output = fields.Selection(
        [
            ('xls', '.Excel'),
            ('pdf', '.PDF'),
        ],
        string='Report Type'
    )

    @api.v7
    def action_print_report(self, data):
        records = []
        report_name = "product.not.sale.report.jasper"
        wizard = self
        start_date = wizard.start_date
        end_date = wizard.end_date
        branch_id = wizard.branch_id
        jasper_output = wizard.jasper_output

        product_not_sale_report = self.env.ref('pos_customize.product_not_sale_report_jasper')

        product_not_sale_report.write({
            'jasper_output': jasper_output,
        })

        # Send parameter to print
        params = {
            'start_date': start_date,
            'end_date': end_date,
            'branch_id': str(branch_id.id),
        }
        data.update({'records': records, 'parameters': params})
        res = {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': data,
        }
        return res
