# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import api, fields, models

__author__ = 'Papatpon'


class BestSellerReport(models.TransientModel):
    _name = 'report.receipt.short.wizard'
    _description = "Report Invoice"

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
        string='Select Branch'
    )

    @api.multi
    def action_print_report(self, data):
        records = []
        report_name = "report.receipt.short.jasper"

        start_date = datetime.strptime(self.start_date, '%Y-%m-%d')
        end_date = datetime.strptime(self.end_date, '%Y-%m-%d')

        params = {
            'start_date': start_date.strftime('%m-%d-%Y'),
            'end_date': end_date.strftime('%m-%d-%Y'),
            'branch_id': str(self.branch_id.id),
        }

        data.update({'records': records, 'parameters': params})
        res = {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': data,
        }
        return res
