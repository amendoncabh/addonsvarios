# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

__author__ = 'Pajaree'

class AnnualSalesReport(models.TransientModel):
    _name = 'annual.sales.report.wizard'
    _description = "Annual Sales Report"



    start_branch = fields.Many2one(
        'pos.branch',
        string='Start Branch'
    )
    end_branch = fields.Many2one(
        'pos.branch',
        string='End Branch'
    )
    year_input = fields.Selection(
        '_years_name',
        string='Year',
        required=True
    )
    jasper_output = fields.Selection(
        [
             ('xls', '.Excel'),
             ('pdf', '.PDF'),
        ],
        string='Report Type'
    )

    def action_print_report(self, data):

        records = []
        report_name = "annual.sales.report.jasper"
        wizard = self
        year_input = wizard.year_input
        start_branch = wizard.start_branch.sequence
        end_branch = wizard.end_branch.sequence
        jasper_output = wizard.jasper_output

        annual_sales_name = self.env.ref('pos_customize.annual_sales_report_jasper')

        annual_sales_name.write({
           'jasper_output': jasper_output,
        })

        #Send parameter to print
        params = {
            'year_input': str(year_input),
            'start_branch': str(start_branch),
            'end_branch': str(end_branch),
        }
        data.update({'records': records, 'parameters': params})
        res = {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': data,
        }
        return res

    @api.model
    def _years_name(self):
        year_time = []
        sql_query = """SELECT date_part('year', date_order ) as order_year
                      from pos_order
                      where date_order is not null
                      group by date_part('year', date_order )"""
        self.env.cr.execute(sql_query)
        years = self.env.cr.dictfetchall()
        for year in years:
               year_time.append((
                    year['order_year'],
                    year['order_year']
               ))
        return year_time
