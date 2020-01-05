# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import api, fields, models


class DailyReturnDetailReport(models.TransientModel):
    _name = 'data.inventory.report.wizard'
    _description = "Data Inventory Report"

    company_id = fields.Many2one(
        'res.company',
        string='Company',
    )
    branch_id = fields.Many2one(
        'pos.branch',
        string='Branch',
    )

    month = fields.Selection(
        string="Month",
        selection=[
            (1, 'มกราคม'),
            (2, 'กุมภาพันธ์'),
            (3, 'มีนาคม'),
            (4, 'เมษายน'),
            (5, 'พฤษภาคม'),
            (6, 'มิถุนายน'),
            (7, 'กรกฎาคม'),
            (8, 'สิงหาคม'),
            (9, 'กันยายน'),
            (10, 'ตุลาคม'),
            (11, 'พฤษจิกายน'),
            (12, 'ธันวาคม'),
        ],
        required=True,
    )

    year = fields.Selection(
        string="Year",
        selection=[(datetime.now().year - i, datetime.now().year - i) for i in range(20)],
        required=True,
    )

    @api.multi
    def action_print_report(self, data):
        records = []

        report_name = 'data.inventory.report.jasper'
        wizard = self
        year = wizard.year
        month = wizard.month
        company_id = wizard.company_id.id
        branch_id = wizard.branch_id.id

        self.env['calculate.average.price.wizard'].check_recalculate_average_price(branch_id)

        # Send parameter to print
        params = {
            'year': str(year),
            'month': str(month),
        }

        if company_id:
            params.update({'company_id': str(company_id)})
        if branch_id:
            params.update({'branch_id': str(branch_id)})

        data.update({'records': records, 'parameters': params})
        res = {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': data,
        }
        return res
