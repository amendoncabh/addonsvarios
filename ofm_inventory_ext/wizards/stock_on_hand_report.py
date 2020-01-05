# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import api, fields, models


class StockOnHandReportWizard(models.TransientModel):
    _name = 'stock.on.hand.report.wizard'
    _description = "Stock On Hand Report"

    from_date = fields.Date(
        string='Date',
        default=(datetime.now() + timedelta(hours=7)).strftime("%Y-%m-%d"),
        required=True
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True
    )

    branch_id = fields.Many2one(
        'pos.branch',
        string='Branch',
        required=True
    )

    @api.multi
    def action_print_report(self, data):
        records = []
        report_name = "stock.on.hand.report.jasper"

        wizard = self
        from_date = wizard.from_date
        company_id = wizard.company_id.id
        branch_id = wizard.branch_id.id

        self.env['calculate.average.price.wizard'].check_recalculate_average_price(branch_id)

        # Send parameter to print
        params = {
            'from_date': from_date
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
