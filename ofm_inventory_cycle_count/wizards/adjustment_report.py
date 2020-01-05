# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from odoo import api, fields, models, _
from datetime import datetime

class AdjustmentReport(models.TransientModel):
    _name = 'adjustment.report.wizard'

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

    @api.multi
    def action_print_report(self, data):
        self.ensure_one()
        records = []

        if self.jasper_output == 'pdf':
            report_name = "adjustment.pdf.jasper"
        else:
            report_name = "adjustment.xls.jasper"

        params = {
           'start_date': self.start_date,
           'end_date': self.end_date,
        }

        if self.company_id:
            params.update({'company_id': str(self.company_id.id)})
        if self.branch_id:
            params.update({'branch_id': str(self.branch_id.id)})
        if self.start_pid:
            params.update({'start_pid': str(self.start_pid)})
        if not self.start_pid:
            params.update({'start_pid': '00000000'})
        if self.end_pid:
            params.update({'end_pid': str(self.end_pid)})
        if not self.end_pid:
            params.update({'end_pid': 'ZZZZZZZZ'})

        data.update({'records': records, 'parameters': params})
        res = {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': data,
        }

        return res