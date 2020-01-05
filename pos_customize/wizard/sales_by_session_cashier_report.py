# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

__author__ = 'Papatpon'


class DiscountByBillReport(models.TransientModel):
    _name = 'sales.by.session.cashier.report.wizard'
    _description = "Sales By Session Cashier Report"

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
    select_report_output = fields.Selection(
        [
            ('1', u'Order by Cash Register'),
            ('2', u'Order by Cashier'),
        ],
        string='Order By',
        default='1'
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
        select_report_output = wizard.select_report_output
        jasper_output = wizard.jasper_output

        sales_by_session_cashier_report = self.env.ref(
            'pos_customize.sales_by_session_cashier_report_jasper'
        )
        # sales_by_cashier_session_report_jasper = self.env.ref(
        #     'pos_customize.sales_by_cashier_session_report_jasper'
        # )

        sales_by_session_cashier_report.write({
            'jasper_output': jasper_output,
        })

        # sales_by_cashier_session_report_jasper.write({
        #     'jasper_output': jasper_output,
        # })

        if select_report_output == '1':
            report_name = "sales.by.session.cashier.report.jasper"

        else:
            # report_name = "sales.by.cashier.session.report.jasper"
            report_name = "sales.by.session.cashier.report.jasper"

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
