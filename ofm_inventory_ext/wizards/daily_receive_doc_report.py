# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class DailyReceiveDocReport(models.TransientModel):
    _name = 'daily.receive.doc.report.wizard'
    _description = "Daily Receive Document Report"

    start_date = fields.Date(
        string='Start Date',
        default=fields.Datetime.now,
    )

    end_date = fields.Date(
        string='End Date',
        default=fields.Datetime.now,
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
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
        string='Report Type',
        default='pdf'
    )

    @api.multi
    def action_print_report(self, data):
        records = []
        if self.jasper_output == 'pdf':
            report_name = "daily.receive.doc.report.pdf.jasper"
        else:
            report_name = "daily.receive.doc.report.excel.jasper"

        wizard = self
        start_date = wizard.start_date
        end_date = wizard.end_date
        start_branch = wizard.start_branch.sequence
        end_branch = wizard.end_branch.sequence
        company_id = wizard.company_id.id

        # Send parameter to print
        params = {
            'start_date': start_date,
            'end_date': end_date,
            'company_id': str(company_id),
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
