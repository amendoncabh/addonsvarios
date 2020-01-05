# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class RawDataSalesReport(models.TransientModel):
    _name = 'raw.data.sales.report.wizard'
    _description = "Data Sales Report"

    start_date = fields.Date(
        string='Start Date',
        default=fields.Datetime.now,
        required=True
    )
    end_date = fields.Date(
        string='End Date',
        default=fields.Datetime.now,
        required=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True
    )
    branch_id = fields.Many2one(
        'pos.branch',
        string='Branch',
        required=True
    )

    @api.multi
    def action_print_report(self, data):
        records = []
        report_name = "raw.data.sales.report.excel.jasper"

        wizard = self
        start_date = wizard.start_date
        end_date = wizard.end_date
        company_id = wizard.company_id.id
        branch_id = wizard.branch_id.id

        self.env['calculate.average.price.wizard'].check_recalculate_average_price(branch_id)

        # Send parameter to print
        params = {
            'start_date': start_date,
            'end_date': end_date
        }
        if company_id:
            params.update({'company_id': str(company_id)})
        if branch_id:
            params.update({'branch_id': str(branch_id)})
        data.update({'records': records, 'parameters': params})
        res = {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': data,
        }
        return res
