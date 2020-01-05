# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models


class DebtorAgedAnalysisSalesReport(models.TransientModel):
    _name = 'debtor.aged.analysis.sales.report.wizard'
    _description = "Debtor Aged Analysis Sales Report"

    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
    )

    branch_id = fields.Many2one(
        'pos.branch',
        string='Branch',
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
        report_name = "debtor.aged.analysis.sales.report.jasper"
        wizard = self
        
        partner_id = wizard.partner_id.id
        company_id = wizard.company_id.id
        branch_id = wizard.branch_id.id
        jasper_output = wizard.jasper_output

        report = self.env.ref('ofm_so_ext.debtor_aged_analysis_sales_report_jasper')
        report.write({
            'jasper_output': jasper_output,
        })
        
        # Send parameter to print
        params = {
        }

        if partner_id:
            params.update({'partner_id': str(partner_id)})
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
