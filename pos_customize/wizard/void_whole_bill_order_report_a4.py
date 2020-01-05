# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

__author__ = 'Pajaree'


class VoidWholeBillReport(models.TransientModel):
    _name = 'void.whole.bill.order.report.a4.wizard'
    _description = "Void Bill Order Report"

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
        report_name = "void.whole.bill.order.report.a4.jasper"
        wizard = self
        start_date = wizard.start_date
        end_date = wizard.end_date
        branch_id = wizard.branch_id.id
        jasper_output = wizard.jasper_output

        void_whole_bill_order_name = self.env.ref(
            'pos_customize.void_whole_bill_order_report_a4_jasper'
        )

        void_whole_bill_order_name.write({
            'jasper_output': jasper_output,
        })

        # Send parameter to print
        params = {
            'start_date': start_date,
            'end_date': end_date,
            'branch_id': str(branch_id),
        }
        data.update({'records': records, 'parameters': params})
        res = {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': data,
        }
        return res
