# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

__author__ = 'Papatpon'


class PaymentTypeByBillReport(models.TransientModel):
    _name = 'payment.type.by.bill.report.wizard'
    _description = "Payment Type By Bill Report"

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
    jasper_output = fields.Selection(
        [
            ('xls', '.Excel'),
            ('pdf', '.PDF'),
        ],
        string='Type Report',
        default='pdf'
    )

    @api.multi
    def action_print_report(self, data):
        records = []

        wizard = self
        start_date = wizard.start_date
        end_date = wizard.end_date
        start_branch = wizard.start_branch.sequence
        end_branch = wizard.end_branch.sequence
        jasper_output = wizard.jasper_output

        payment_type_by_bill_report = self.env.ref(
            'pos_customize.payment_type_by_bill_report_jasper'
        )

        payment_type_by_bill_report.write({
            'jasper_output': jasper_output,
        })

        report_name = "payment.type.by.bill.report.jasper"

        # Send parameter to print
        params = {
            'date_start': start_date,
            'date_stop': end_date,
            'branch_start': str(start_branch),
            'branch_stop': str(end_branch),
        }

        data.update({'records': records, 'parameters': params})
        res = {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': data,
        }
        return res
