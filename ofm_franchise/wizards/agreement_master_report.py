# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AgreementMasterReport(models.TransientModel):
    _name = 'agreement.master.report.wizard'
    _description = "Agreement Master Report"


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

    company_id = fields.Many2one(
        'res.company',
        string='Company',
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

    start_date = fields.Date(
        string='Start Date',
        default=fields.Datetime.now,
    )

    end_date = fields.Date(
        string='End Date',
        default=fields.Datetime.now,
    )

    state = fields.Selection(
        selection=[
           ('pending', 'Pending'),
           ('active', 'Active'),
           ('closed', 'Closed'),
        ],
        default='pending',
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
        report_name = "agreement.master.report.jasper"

        wizard = self
        company_id = wizard.company_id.id
        branch_id = wizard.branch_id.id
        start_date = wizard.start_date
        end_date = wizard.end_date
        state = wizard.state
        jasper_output = wizard.jasper_output

        report = self.env.ref('ofm_franchise.agreement_master_report_jasper')
        report.write({
            'jasper_output': jasper_output,
        })

        # Send parameter to print
        params = {
        }

        if company_id:
            params.update({'company_id': str(company_id)})
        if branch_id:
            params.update({'branch_id': str(branch_id)})
        if start_date:
            params.update({'start_date': start_date})
        if end_date:
            params.update({'end_date': end_date})
        if state:
            params.update({'state': str(state)})

        data.update({'records': records, 'parameters': params})
        res = {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': data,
        }
        return res
