# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class POAmountReport(models.TransientModel):
    _name = 'po.amount.report.wizard'
    _description = "PO Amount Report"

    def get_year(self):
        return datetime.date.today().strftime("%Y")

    def get_month(self):
        return datetime.date.today().strftime("%m")

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.user.company_id,
    )

    branch_id = fields.Many2one(
        'pos.branch',
        string='Branch',
        default=lambda self: self.env.user.branch_id,
    )

    month = fields.Selection(
        string="Month",
        selection=[
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
            ('11', 'พฤษจิกายน'),
            ('12', 'ธันวาคม'),
        ],
        required=True,
        default=get_month,
    )

    year = fields.Selection(
        string="Year",
        selection=[
            ('2014', '2014'),
            ('2015', '2015'),
            ('2016', '2016'),
            ('2017', '2017'),
            ('2018', '2018'),
            ('2019', '2019'),
            ('2020', '2020'),
            ('2021', '2021'),
            ('2022', '2022'),
            ('2023', '2023'),
            ('2024', '2024'),
            ('2025', '2025'),
            ('2026', '2026'),
            ('2027', '2027'),
            ('2028', '2028'),
            ('2029', '2029'),
            ('2030', '2030'),
            ('2031', '2031'),
            ('2032', '2032'),
            ('2033', '2033'),
            ('2034', '2034'),
            ('2035', '2035'),
            ('2036', '2036'),
            ('2037', '2037'),
            ('2038', '2038'),
        ],
        required=True,
        default=get_year,
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
        report_name = "po.amount.report.jasper"
        wizard = self

        company_id = wizard.company_id.id
        branch_id = wizard.branch_id.id
        month = wizard.month
        year = wizard.year
        jasper_output = wizard.jasper_output

        report = self.env.ref('ofm_purchases_ext.po_amount_report_jasper')
        report.write({
            'jasper_output': jasper_output,
        })

        start_date = datetime.date(year=int(year), day=01, month=int(month))
        end_date = start_date + relativedelta(months=1) - relativedelta(days=1)
        end_next_date = end_date + relativedelta(days=1)
        start_date = start_date.strftime("%Y-%m-%d")
        end_date = end_date.strftime("%Y-%m-%d")
        end_next_date = end_next_date.strftime("%Y-%m-%d")
        
        # Send parameter to print
        params = {
            'start_date': start_date,
            'end_date': end_date,
            'end_next_date': end_next_date,
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
