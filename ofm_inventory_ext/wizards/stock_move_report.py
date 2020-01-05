# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class StockMoveReport(models.TransientModel):
    _name = 'stock.move.report.wizard'
    _description = "Stock Move Report"

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
        default=lambda self: self.env.user.company_id,
        required=False,
    )

    branch_id = fields.Many2one(
        'pos.branch',
        string='Branch',
        default=lambda self: self.env.user.branch_id,
        required=False,
    )

    start_pid = fields.Char(
        string="Start PID",
        required=False,
    )

    end_pid = fields.Char(
        string="End PID",
        required=False,
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

    status_type = fields.Selection(
        selection=[
            ('more_zero', 'รายการขาย'),
            ('less_zero', 'รายการรับคืน'),
            ('all', 'รายการขายและรับคืน'),
        ],
        default='all',
        string='Move Type'
    )

    @api.multi
    def action_print_report(self, data):
        records = []
        wizard = self
        start_date = wizard.start_date
        end_date = wizard.end_date
        company_id = wizard.company_id.id
        branch_id = wizard.branch_id.id
        start_pid = wizard.start_pid
        end_pid = wizard.end_pid
        status_type = wizard.status_type

        self.env['calculate.average.price.wizard'].check_recalculate_average_price(branch_id)

        if wizard.jasper_output == 'pdf':
            report_name = "stock.move.report.pdf.jasper"
        else:
            report_name = "stock.move.report.excel.jasper"

        # Send parameter to print
        params = {
           'start_date': start_date,
           'end_date': end_date,
        }
        params.update({'status_type': str(status_type)})

        if company_id:
            params.update({'company_id': str(company_id)})
        if branch_id:
            params.update({'branch_id': str(branch_id)})
        if start_pid:
            params.update({'start_pid': str(start_pid)})
        if not start_pid:
            params.update({'start_pid': '00000000'})
        if end_pid:
            params.update({'end_pid': str(end_pid)})
        if not end_pid:
            params.update({'end_pid': 'ZZZZZZZZ'})

        data.update({'records': records, 'parameters': params})
        res = {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': data,
        }

        return res
