# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

__author__ = 'Papatpon'

class DailySaleDetailReport(models.TransientModel):
    _name = 'daily.sale.detail.report.wizard'
    _description = "Daily Sales Detail Report"

    start_date = fields.Date(
        string='Date',
        default=fields.Datetime.now,
    )

    branch_id = fields.Many2one(
        'pos.branch',
        string='Branch'
    )

    @api.multi
    def action_print_report(self, data):
        records = []
        report_name = "daily.sale.detail.report.jasper"
        wizard = self
        start_date = wizard.start_date
        branch_id = wizard.branch_id

        #Send parameter to print
        params= {
            'start_date': start_date,
            'branch_id': str(branch_id.id),
        }
        data.update({'records': records, 'parameters': params})
        res = {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': data,
        }
        return res
