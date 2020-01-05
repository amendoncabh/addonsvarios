# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models


class DepositSalesAllCashierReport(models.TransientModel):
    _name = 'deposit.sales.all.cashier.report.wizard'
    _description = "Deposit Sales All Cashier Report"

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

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
    )

    branch_id = fields.Many2one(
        'pos.branch',
        string='Branch',
        required=True,
    )

    user_id = fields.Many2one(
        comodel_name='res.users',
        string='Salesperson',
        index=True,
        track_visibility='onchange',
    )

    jasper_output = fields.Selection(
        [
            ('xls', '.Excel'),
            ('pdf', '.PDF'),
        ],
        string='Report Type',
        default='pdf',
        required=True,
    )

    @api.multi
    def action_print_report(self, data):
        records = []
        report_name = "deposit.sales.all.cashier.report.jasper"
        wizard = self

        start_date = wizard.start_date
        end_date = wizard.end_date
        company_id = wizard.company_id.id
        branch_id = wizard.branch_id.id
        user_id = wizard.user_id.id
        jasper_output = wizard.jasper_output

        report = self.env.ref('ofm_so_ext.deposit_sales_all_cashier_report_jasper')
        report.write({
            'jasper_output': jasper_output,
        })
        
        end_next_date = datetime.strptime(end_date, DEFAULT_SERVER_DATE_FORMAT) + relativedelta(days=1)
        end_next_date = end_next_date.strftime(DEFAULT_SERVER_DATE_FORMAT)
        # Send parameter to print
        params = {
            'start_date': start_date,
            'end_date': end_date,
            'end_next_date': end_next_date,
        }

        if company_id:
            params.update({'company_id': str(company_id)})
        if branch_id:
            params.update({'branch_id': str(branch_id)})
        if user_id:
            params.update({'user_id': str(user_id)})
        data.update({'records': records, 'parameters': params})
        res = {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': data,
        }
        return res
