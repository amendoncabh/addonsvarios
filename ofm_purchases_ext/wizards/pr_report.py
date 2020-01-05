# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PrReport(models.TransientModel):
    _name = 'pr.report.wizard'
    _description = "Pr Report"

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

    po_no = fields.Char(
        string="PO No.",
        required=False,
    )

    start_date = fields.Date(
        string='PO Start Date',
        default=fields.Datetime.now,
        required=True,
    )

    end_date = fields.Date(
        string='PO End Date',
        default=fields.Datetime.now,
        required=True,
    )

    po_status = fields.Many2many(
        'po.status',
        string='PO Status',
        domain=[('value', '!=', 'purchase')],
        required=True
    )

    product_status = fields.Many2many(
        'product.status',
        string='Product Status',
        required=True
    )

    type_to_ofm = fields.Many2many(
        'type.to.ofm',
        string='Type To OFM',
        required=True
    )

    @api.multi
    def action_print_report(self, data):
        records = []
        report_name = "pr.report.jasper"
        wizard = self

        if not wizard.po_status or not wizard.product_status or not wizard.type_to_ofm:
            raise UserError(_('Please check field PR Status, Product Status, Type To OFM before print rePrt'))

        company_id = wizard.company_id.id
        branch_id = wizard.branch_id.id
        po_no = wizard.po_no
        start_date = wizard.start_date
        end_date = wizard.end_date

        product_status = ''
        for item in wizard.product_status:
            product_status += str(',' + item.value + ',')

        po_status = ''
        for item in wizard.po_status:
            po_status += str(',' + item.value + ',')

        type_to_ofm = ''
        for item in wizard.type_to_ofm:
            type_to_ofm += str(',' + item.value + ',')

        # Send parameter to print
        params = {
            'company_id': str(company_id),
            'branch_id': str(branch_id),
            'start_date': start_date,
            'end_date': end_date,
            'po_status': po_status,
            'type_to_ofm': type_to_ofm,
            'product_status': product_status,
        }

        if po_no:
            params.update({'po_no': po_no})

        if wizard.product_status.filtered(lambda pro_status: pro_status.value == 'All'):
            del params['product_status']

        data.update({'records': records, 'parameters': params})
        res = {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': data,
        }
        return res
