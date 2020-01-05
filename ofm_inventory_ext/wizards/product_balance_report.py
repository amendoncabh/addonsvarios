# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo import api, fields, models


class ProductBalanceReport(models.TransientModel):
    _name = 'product.balance.report.wizard'
    _description = "Product Balance Report"

    month = fields.Selection(
        [
            ('1', 'มกราคม'),
            ('2', 'กุมภาพันธ์'),
            ('3', 'มีนาคม'),
            ('4', 'เมษายน'),
            ('5', 'พฤษภาคม'),
            ('6', 'มิถุนายน'),
            ('7', 'กรกฎาคม'),
            ('8', 'สิงหาคม'),
            ('9', 'กันยายน'),
            ('10', 'ตุลาคม'),
            ('11', 'พฤศจิกายน'),
            ('12', 'ธันวาคม'),
        ],
        string='Month',
        default=str(datetime.datetime.now().month),
        type='selection',
    )
    year = fields.Selection(
        string="Year",
        default=datetime.datetime.now().year,
        selection=[(datetime.datetime.now().year - i, datetime.datetime.now().year - i) for i in range(20)],
        required=True,
    )
    product_cate_ids = fields.Many2many(
        'product.category',
        string='Product Category'
    )
    product_all_ids = fields.Many2many(
        'product.template',
        string='Product'
    )
    product_filter_ids = fields.Many2many(
        'product.template',
        string='Product'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.user.company_id
    )
    branch_id = fields.Many2one(
        'pos.branch',
        string='Branch',
        default=lambda self: self.env.user.branch_id

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

    @api.model
    @api.onchange('product_cate_ids')
    def _onchange_product_category(self):
        self.product_all_ids = None
        self.product_filter_ids = None

    @api.multi
    def action_print_report(self, data):
        records = []
        wizard = self
        month = wizard.month
        year = wizard.year
        product_cate_ids = wizard.product_cate_ids.ids
        product_all_ids = wizard.product_all_ids.ids
        product_filter_ids = wizard.product_filter_ids.ids
        company_id = wizard.company_id.id
        branch_id = wizard.branch_id.id

        self.env['calculate.average.price.wizard'].check_recalculate_average_price(branch_id)

        if wizard.jasper_output == 'pdf':
            report_name = "product.balance.report.pdf.jasper"
        else:
            report_name = "product.balance.report.excel.jasper"

        # Send parameter to print
        params = {
            'month': str(month),
            'year': str(year),
        }
        if product_cate_ids:
            params.update({'product_cate_ids': ','.join(map(str, product_cate_ids))})
        if product_all_ids:
            params.update({'product_ids': ','.join(map(str, product_all_ids))})
        elif product_filter_ids:
            params.update({'product_ids': ','.join(map(str,product_filter_ids))})
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
