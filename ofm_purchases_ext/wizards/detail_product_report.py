# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProductBalanceReport(models.TransientModel):
    _name = 'detail.product.report.wizard'
    _description = "Detail Product Report"

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

    back_month = fields.Selection(
        [
            ('back_month3', 'สินค้ายอดขาย 3 เดือน'),
            ('back_month6', 'สินค้ายอดขาย 6 เดือน'),
            ('back_month12', 'สินค้ายอดขาย 12 เดือน'),
        ],
        string='ยอดขายย้อนหลัง',
        default='back_month3',
        required=True,
    )

    product_status = fields.Many2many(
        'product.status',
        string='Product Status',
        required=True
    )

    check_zero = fields.Boolean(
        string='สินค้าคงเหลือเป็น 0',
        default=False,
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
        checkzero = wizard.check_zero

        if not wizard.product_status:
            raise UserError(_('Please check field Product Status'))

        product_status = ''
        for item in wizard.product_status:
            product_status += str(',' + item.value + ',')

        self.env['calculate.average.price.wizard'].check_recalculate_average_price(branch_id)

        if wizard.back_month == 'back_month3':
            report_name = "detail.product.report.excel.jasper"
        elif wizard.back_month == 'back_month6':
            report_name = "detail.product.report.excel.6.jasper"
        elif wizard.back_month == 'back_month12':
            report_name = "detail.product.report.excel.12.jasper"

        # Send parameter to print
        params = {
            'month': str(month),
            'year': str(year),
            'checkzero': str(checkzero),
            'product_status': product_status,
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
        if wizard.product_status.filtered(lambda pro_status: pro_status.value == 'All'):
            del params['product_status']

        data.update({'records': records, 'parameters': params})
        res = {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': data,
        }
        return res
