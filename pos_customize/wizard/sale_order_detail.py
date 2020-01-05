# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

__author__ = 'Pajaree'


class SaleOrderDetailReport(models.TransientModel):
    _name = 'sale.order.detail.report.wizard'
    _description = "Sale by Day Report"

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
    start_category = fields.Many2one(
        'product.category',
        string='Start Category'
    )
    end_category = fields.Many2one(
        'product.category',
        string='End Category'
    )
    start_branch = fields.Many2one(
        'pos.branch',
        string='Start Branch'
    )
    end_branch = fields.Many2one(
        'pos.branch',
        string='End Branch'
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
        report_name = "sale.order.detail.report.jasper"
        wizard = self
        start_date = wizard.start_date
        end_date = wizard.end_date
        start_category = wizard.start_category.id
        end_category = wizard.end_category.id
        start_branch = wizard.start_branch.sequence
        end_branch = wizard.end_branch.sequence
        jasper_output = wizard.jasper_output

        sale_order_detail_name = self.env.ref('pos_customize.sale_order_detail_report_jasper')

        sale_order_detail_name.write({
            'jasper_output': jasper_output,
        })

        # Send parameter to print
        params = {
            'start_date': start_date,
            'end_date': end_date,
            'start_category': str(start_category),
            'end_category': str(end_category),
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
