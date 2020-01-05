# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

__author__ = 'Cash'

class SaleSummaryForAllPosReport(models.TransientModel):
    _name = 'sale.summary.for.all.pos.report'
    _description = "Sale summary for all pos report"

    start_date = fields.Date(
        string='Start Date',
        default=fields.Datetime.now,
    )
    end_date = fields.Date(
        string='From Date',
        default=fields.Datetime.now,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company'
    )

    branch_id = fields.Many2one(
        'pos.branch',
        string='Branch'
    )

    @api.multi
    def action_print_report(self, data):
        records = []
        report_name = "sale.summary.for.all.pos.report.jasper"
        wizard = self

        start_date = wizard.start_date
        end_date = wizard.end_date
        company_id = wizard.company_id.id
        branch_id = wizard.branch_id.id

        # Send parameter to print
        params = {
            'start_date': start_date,
            'end_date': end_date,
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