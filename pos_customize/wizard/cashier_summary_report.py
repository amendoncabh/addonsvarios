# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

__author__ = 'Papatpon'

class AnnualSalesReport(models.TransientModel):
    _name = 'cashier.summary.report.wizard'
    _description = "Cashier Summary Report"

    branch_id = fields.Many2one(
        'pos.branch',
        string='Branch',
        required=True
    )
    year_input = fields.Char(
        string='Year',
        required=True
    )
    price_input = fields.Char(
        string='Price',
        required=True
    )
    round_input = fields.Char(
        string='Round Limit',
        required=True
    )
    month_input = fields.Selection(
        [
            ('01', 'มกราคม'),
            ('02', 'กุมภาพันธ์'),
            ('03', 'มีนาคม'),
            ('04', 'เมษายน'),
            ('05', 'พฤษภาคม'),
            ('06', 'มิถุนายน'),
            ('07', 'กรกฎาคม'),
            ('08', 'สิงหาคม'),
            ('09', 'กันยายน'),
            ('10', 'ตุลาคม'),
            ('11', 'พฤศจิกายน'),
            ('12', 'ธันวาคม')
        ],
        string='Month',
        required=True
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
        report_name = "cashier.summary.report.jasper"
        wizard = self
        branch_id = wizard.branch_id
        price_input = wizard.price_input
        round_input = wizard.round_input
        year_input = wizard.year_input
        month_input = wizard.month_input
        jasper_output = wizard.jasper_output
        cashier_summary_report_name = self.env.ref('pos_customize.cashier_summary_report_jasper')

        cashier_summary_report_name.write({
           'jasper_output': jasper_output,
        })

        #Send parameter to print
        params = {
            'year': str(year_input),
            'branch': str(branch_id.id),
            'period': str(month_input),
            'price': str(price_input),
            'round_limit': str(round_input),
        }
        data.update({'records': records, 'parameters': params})
        res = {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': data,
        }
        return res
