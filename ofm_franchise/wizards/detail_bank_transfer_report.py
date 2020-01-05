# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class DetailBankTransferReport(models.TransientModel):
    _name = 'detail.bank.transfer.report.wizard'
    _description = "Detail Bank Transfer Report"

    def _get_default_required(self):
        result = True if len(self.env.user.groups_id.filtered(lambda groups: groups.name == 'HQ')) == 0 else False

        return result

    def _get_default_company(self):
        result = self.env.user.company_id if len(self.env.user.groups_id.filtered(
            lambda groups: groups.name == 'HQ')
        ) == 0 else None

        return result

    def _get_default_branch(self):
        result = self.env.user.branch_id if len(self.env.user.groups_id.filtered(
            lambda groups: groups.name == 'HQ')
        ) == 0 else None

        return result

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
        required=False,
        default=_get_default_company,
        placeholder='All',
    )

    branch_id = fields.Many2one(
        'pos.branch',
        string='Branch',
        required=False,
        default=_get_default_branch,
        placeholder='All',
    )

    is_required = fields.Boolean(
        string="",
        default=_get_default_required,
    )

    @api.multi
    def action_print_report(self, data):
        records = []
        report_name = "detail.bank.transfer.report.jasper"

        wizard = self
        start_date = wizard.start_date
        end_date = wizard.end_date
        company_id = wizard.company_id.id
        branch_id = wizard.branch_id.id

        # Send parameter to print
        params = {
            'start_date': start_date,
            'end_date': end_date
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
