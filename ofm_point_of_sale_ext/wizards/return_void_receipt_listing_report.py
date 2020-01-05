# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SummaryReceivedProductReturnReport(models.TransientModel):
    _name = 'return.void.receipt.listing.wizard'
    _description = "Return / Void Receipt Listing Report"

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
        default=lambda self: self.env.user.company_id,
    )

    branch_id = fields.Many2one(
        'pos.branch',
        string='Branch',
        default=lambda self: self.env.user.branch_id
    )

    data_type = fields.Selection(
        [
            ('Return', 'Return'),
            ('Void', 'Void'),
        ],
        string='Type',
        required=False,
    )

    data_type = fields.Selection(
        [
            ('Return', 'Return'),
            ('Void', 'Void'),
        ],
        string='Type',
        required=False,
    )

    jasper_output = fields.Selection(
        [
            ('xls', '.Excel'),
            # ('pdf', '.PDF'),
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
            report_name = "return.void.receipt.listing.report.jasper.excel"
        else:
            report_name = "return.void.receipt.listing.report.jasper.pdf"

        start_date = wizard.start_date
        end_date = wizard.end_date
        company_id = wizard.company_id.id
        branch_id = wizard.branch_id.id
        data_type = wizard.data_type

        # Send parameter to print
        params = {
            'start_date': start_date,
            'end_date': end_date,
        }

        if company_id:
            params.update({'company_id': str(company_id)})
        if branch_id:
            params.update({'branch_id': str(branch_id)})
        if data_type:
            params.update({'data_type': data_type})

        data.update({'records': records, 'parameters': params})
        res = {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': data,
        }

        return res
