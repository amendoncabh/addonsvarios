# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ReceiveControlByCashierReport(models.TransientModel):
    _name = 'receive.control.by.cashier.report.wizard'
    _description = "Receive Control By Cashier Report"

    start_date = fields.Date(
        string='Start Date',
        default=fields.Datetime.now,
        required=True,
    )
    end_date = fields.Date(
        string='End Date',
        default=fields.Datetime.now,
        required=True,
    )
    branch_id = fields.Many2one(
        'pos.branch',
        string='Branch',
        required=True,
    )
    cashier_id = fields.Many2one(
        'res.users',
        string='Cashier',
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
        if self.jasper_output == 'pdf':
            report_name = "receive.control.by.cashier.report.excel.jasper"
        else:
            report_name = "receive.control.by.cashier.report.excel.jasper"

        wizard = self
        start_date = wizard.start_date
        end_date = wizard.end_date
        branch_id = str(wizard.branch_id.id)

        # Send parameter to print
        params = {
            'start_date': start_date,
            'end_date': end_date,
            'branch_id': branch_id,
        }

        if wizard.cashier_id.id:
            params.update({'cashier_id': str(wizard.cashier_id.id)})

        data.update({'records': records, 'parameters': params})
        res = {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': data,
        }
        return res
