# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

__author__ = 'Pajaree'


class FullTaxInvoiceReport(models.TransientModel):
    _name = 'so.return.product.report.wizard'
    _description = "Return Product Report"

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

    branch_id = fields.Many2one(
        'pos.branch',
        string='Branch',
    )

    jasper_output = fields.Selection(
        [
            ('xls', '.Excel'),
            ('pdf', '.PDF'),
        ],
        string='Report Type',
        default='xls',
        required=True,
    )

    @api.multi
    def action_print_report(self, data):
        records = []
        wizard = self

        if wizard.jasper_output == 'xls':
            report_name = "return.product.report.jasper.excel"
        else:
            report_name = "return.product.report.jasper.pdf"

        start_date = wizard.start_date
        end_date = wizard.end_date
        company_id = wizard.company_id.id
        branch_id = wizard.branch_id.id

        # Send parameter to print
        params = {
            'start_date': start_date,
            'end_date': end_date,
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
