# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

__author__ = 'Papatpon'


class HourlySaleVolumeReport(models.TransientModel):
    _name = 'hourly.sale.product.line.by.cat.wizard'
    _description = "Hourly Sale Product Lines By Category"

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
        report_name = "hourly.sale.product.line.by.cat.jasper"
        wizard = self
        start_date = wizard.start_date
        end_date = wizard.end_date
        start_branch = wizard.start_branch.sequence
        end_branch = wizard.end_branch.sequence
        start_cate = wizard.start_cate.sequence
        end_cate = wizard.end_cate.sequence
        jasper_output = wizard.jasper_output

        hourly_sale_volume_name = self.env.ref('pos_customize.hourly_sale_product_line_by_cat_jasper')

        hourly_sale_volume_name.write({
            'jasper_output': jasper_output,
        })

        # Send parameter to print
        params = {
            'start_date': start_date,
            'end_date': end_date,
            'start_branch': str(start_branch),
            'end_branch': str(end_branch),
            'start_category': str(start_cate),
            'end_category': str(end_cate),
        }
        data.update({'records': records, 'parameters': params})
        res = {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': data,
        }
        return res
