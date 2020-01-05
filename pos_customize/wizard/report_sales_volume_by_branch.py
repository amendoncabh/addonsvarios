# -*- coding: utf-8 -*- 
# Part of Odoo. See LICENSE file for full copyright and licensing details. 

from odoo import api, fields, models

__author__ = 'wine'


class ReportSalesVolumeByBranch(models.TransientModel):
    _name = 'report.sales.volume.by.branch.wizard'
    _description = "Report Sales Volume By Branch"

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
    start_cate = fields.Many2one(
        'product.category',
        string='Start Category'
    )
    end_cate = fields.Many2one(
        'product.category',
        string='End Category'
    )
    jasper_output = fields.Selection(
        [
            ('xls', '.Excel'),
            ('pdf', '.PDF'),
        ],
        string='Report Type'
    )

    @api.multi
    def action_print_report(self, data):
        records = []
        report_name = "report.sales.volume.by.branch.jasper"
        wizard = self
        start_date = wizard.start_date
        end_date = wizard.end_date
        start_branch = wizard.start_branch.sequence
        end_branch = wizard.end_branch.sequence
        start_cate = wizard.start_cate.sequence
        end_cate = wizard.end_cate.sequence
        jasper_output = wizard.jasper_output

        sales_volume_by_branch_name = self.env.ref('pos_customize.report_sales_volume_by_branch_jasper')

        sales_volume_by_branch_name.write({
            'jasper_output': jasper_output,
        })

        # Send parameter to print
        params = {
            'date_start': start_date,
            'date_end': end_date,
            'start_cate': str(start_cate),
            'end_cate': str(end_cate),
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
