# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ReturnDetailReport(models.TransientModel):
    _name = 'return.detail.report.wizard'
    _description = "Return Detail Report"

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
    dept_ids = fields.Many2many(
        string='Dept',
        comodel_name='ofm.product.dept',
        domain=[
            ('dept_parent_id', '=', False)
        ],
    )
    return_reason_ids = fields.Many2many(
        string='Return Reason',
        comodel_name='return.reason',
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.user.company_id,
    )

    branch_id = fields.Many2one(
        'pos.branch',
        string='Branch',
        required=True,
        default=lambda self: self.env.user.branch_id,
    )

    @api.multi
    def action_print_report(self, data):
        records = []
        report_name = "return.detail.report.jasper"
        wizard = self

        start_date = wizard.start_date
        end_date = wizard.end_date
        company_id = wizard.company_id.id
        branch_id = wizard.branch_id.id
        dept_ids = wizard.dept_ids.ids
        return_reason_ids = wizard.return_reason_ids.ids

        sales_report = self.env.ref('ofm_point_of_sale_ext.return_detail_report_jasper')
        sales_report.write({
            'jasper_output': 'xls',
        })

        # Send parameter to print
        params = {
            'start_date': start_date,
            'end_date': end_date,
            'company_id': str(company_id),
            'branch_id': str(branch_id),
        }
        if dept_ids:
            params.update({'dept_ids': ','.join(map(str, dept_ids))})
        if return_reason_ids:
            params.update({'return_reason_ids': ','.join(map(str, return_reason_ids))})

        data.update({'records': records, 'parameters': params})
        res = {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': data,
        }

        return res
