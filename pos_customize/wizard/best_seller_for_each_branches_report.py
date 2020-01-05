# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

__author__ = 'Pajaree'

class BestSellerReport(models.TransientModel):
    _name = 'best.seller.for.each.branches.report.wizard'
    _description = "Best Seller for Each Branches Report"

    start_date = fields.Date(
        string='Start Date',
        default=fields.Datetime.now,
    )
    end_date = fields.Date(
        string='End Date',
        default=fields.Datetime.now,
    )
    start_branch = fields.Many2one(
        'pos.branch',
        string='Start Branch'
    )
    end_branch = fields.Many2one(
        'pos.branch',
        string='End Branch'
    )
    sort_by_type = fields.Selection(
        '_sort_by_type',
        string='Sort by Types',
        required=True
    )
    jasper_output = fields.Selection(
        [
             ('xls', '.Excel'),
             ('pdf', '.PDF'),
        ],
         string = 'Report Type'
    )

    @api.multi
    def action_print_report(self, data):
        records = []
        report_name = "best.seller.for.each.branches.report.jasper"
        wizard = self
        start_date = wizard.start_date
        end_date = wizard.end_date
        start_branch = wizard.start_branch.sequence
        end_branch = wizard.end_branch.sequence
        sort_by_type = wizard.sort_by_type
        jasper_output = wizard.jasper_output

        best_seller_name = self.env.ref('pos_customize.best_seller_for_each_branches_report_jasper')

        best_seller_name.write({
           'jasper_output': jasper_output,
        })

        #Send parameter to print
        params = {
            'start_date': start_date,
            'end_date': end_date,
            'start_branch': str(start_branch),
            'end_branch': str(end_branch),
            'sort_by_type': str(sort_by_type),
        }
        data.update({'records': records, 'parameters': params})
        res = {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': data,
        }
        return res

    @api.model
    def _sort_by_type(self):
        start_time = 0
        end_time = 3
        time_start_arr = []
        sort = ["เรียงตามลำดับสินค้า","เรียงตามจำนวนเงิน","เรียงตามจำนวนสินค้า"]
        for i in xrange(start_time, end_time):
            time_start_arr.append((str(i),sort[i]))
        return time_start_arr
