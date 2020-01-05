# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

__author__ = 'Pajaree'


class FullTaxInvoiceReport(models.TransientModel):
    _name = 'full.tax.invoice.report.wizard'
    _description = "Full Tax Invoice Report"

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

    @api.multi
    def action_print_report(self, data):
        records = []
        report_name = "full.tax.invoice.report.jasper"
        wizard = self
        start_date = wizard.start_date
        end_date = wizard.end_date
        start_branch = wizard.start_branch.sequence
        end_branch = wizard.end_branch.sequence

        # Send parameter to print
        params = {
            'start_date': start_date,
            'end_date': end_date,
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
