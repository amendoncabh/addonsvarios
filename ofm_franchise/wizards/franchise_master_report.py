# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class FranchiseMasterReport(models.TransientModel):
    _name = 'franchise.master.report.wizard'
    _description = "Franchise Master Report"


    def _get_default_company(self):
        result = self.env.user.company_id if len(self.env.user.groups_id.filtered(
            lambda groups: groups.name == 'HQ')
        ) == 0 else None

        return result

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=_get_default_company,
        placeholder='All',
    )

    company_type = fields.Selection(
        string='Company Type',
        selection=[
           ('personal', 'Personal'),
           ('corporate', 'Corporate'),
        ],
    )

    state = fields.Selection(
        selection=[
           ('active', 'Active'),
           ('expire', 'Expire'),
           ('cancel', 'Cancel'),
        ],
        default='active',
    )

    province_id = fields.Many2one(
        'province',
        string='Province',
        track_visibility='always',
    )

    vat = fields.Char(
        string="Tax ID",
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
        report_name = "franchise.master.report.jasper"

        wizard = self
        company_id = wizard.company_id.id
        company_type = wizard.company_type
        state = wizard.state
        province_id = wizard.province_id.id
        vat = wizard.vat
        jasper_output = wizard.jasper_output

        report = self.env.ref('ofm_franchise.franchise_master_report_jasper')
        report.write({
            'jasper_output': jasper_output,
        })

        # Send parameter to print
        use_com_id = self.env.user.company_id.id
        params = {
            'use_com_id': str(use_com_id),
        }

        if company_id:
            params.update({'company_id': str(company_id)})
        if company_type:
            params.update({'company_type': str(company_type)})
        if state:
            params.update({'state': str(state)})
        if province_id:
            params.update({'province_id': str(province_id)})
        if vat:
            params.update({'vat': str(vat)})

        data.update({'records': records, 'parameters': params})
        res = {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': data,
        }
        return res
