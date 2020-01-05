# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

__author__ = 'Papatpon'


class SummarySalesTaxReport(models.TransientModel):
    _name = 'summary.sales.tax.report.wizard'
    _description = "Summary Sales Tax Report"

    start_date = fields.Date(
        string='Start Date',
        default=fields.Datetime.now,
    )
    end_date = fields.Date(
        string='End Date',
        default=fields.Datetime.now,
    )
    start_branch = fields.Many2one(
        'pos.branch',
        string='Start Branch',
        domain=[('id', '=', False)]
    )
    end_branch = fields.Many2one(
        'pos.branch',
        string='End Branch',
        domain=[('id', '=', False)]
    )
    pos_company_id = fields.Many2one(
        'res.company',
        string='Company Select'
    )
    jasper_output = fields.Selection(
        [
            ('xls', '.Excel'),
            ('pdf', '.PDF'),
        ],
        string='Report Type'
    )
    only_sale_amount = fields.Boolean(
        'Show only Branches with sales',
        default=False,
    )

    @api.onchange('pos_company_id')
    def onchange_pos_company_id(self):
        domain = {
            'start_branch': [('id', '=', False)],
            'end_branch': [('id', '=', False)],
        }
        if not self.pos_company_id:

            return {'domain': domain}

        else:

            branch_ids = self.env['pos.branch'].search([
                ('pos_company_id', '=', self.pos_company_id.id)
            ])
            domain['start_branch'] = [('id', 'in', branch_ids.ids)]
            domain['end_branch'] = [('id', 'in', branch_ids.ids)]

        return {'domain': domain}

    @api.multi
    def action_print_report(self, data):
        records = []
        report_name = "summary.sales.tax.report.jasper"
        wizard = self
        start_date = wizard.start_date
        end_date = wizard.end_date
        pos_company_id = wizard.pos_company_id
        jasper_output = wizard.jasper_output
        start_branch = wizard.start_branch.sequence
        end_branch = wizard.end_branch.sequence
        only_sale_amount = wizard.only_sale_amount

        summary_sales_tax_report_name = self.env.ref(
            'pos_customize.summary_sales_tax_report_jasper'
        )

        summary_sales_tax_report_name.write({
            'jasper_output': jasper_output,
        })

        # Send parameter to print
        params = {
            'start_date': start_date,
            'end_date': end_date,
            'pos_company_id': str(pos_company_id.id),
            'start_branch': str(start_branch),
            'end_branch': str(end_branch),
            'only_sale_amount': str(only_sale_amount),
        }
        data.update({'records': records, 'parameters': params})
        res = {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': data,
        }
        return res
