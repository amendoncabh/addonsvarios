# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ReceivedProductReport(models.TransientModel):
    _name = 'received.product.report.wizard'
    _description = "Received Product Report"

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

    rd_start_date = fields.Date(
        string='RD Start Date',
        default=fields.Datetime.now,
        required=True,
    )

    rd_end_date = fields.Date(
        string='RD End Date',
        default=fields.Datetime.now,
        required=True,
    )

    rd_no = fields.Char(
        string="RD No.",
        required=False,
    )

    po_no = fields.Char(
        string="PO No.",
        required=False,
    )

    col_inv_no = fields.Char(
        string="COL Invoice No.",
        required=False,
    )

    inv_start_date = fields.Date(
        string='Invoice Start Date',
        required=False,
    )

    inv_end_date = fields.Date(
        string='Invoice End Date',
        required=False,
    )

    product_code = fields.Char(
        string="Product Code",
        required=False,
    )

    @api.multi
    def action_print_report(self, data):
        records = []
        report_name = "received.product.report.jasper"
        wizard = self
        company_id = wizard.company_id.id
        branch_id = wizard.branch_id.id
        rd_start_date = wizard.rd_start_date
        rd_end_date = wizard.rd_end_date
        rd_no = wizard.rd_no
        po_no = wizard.po_no
        col_inv_no = wizard.col_inv_no
        inv_start_date = wizard.inv_start_date
        inv_end_date = wizard.inv_end_date
        product_code = wizard.product_code

        # Send parameter to print
        params = {
            'company_id': str(company_id),
            'branch_id': str(branch_id),
            'rd_start_date': rd_start_date,
            'rd_end_date': rd_end_date,
        }

        if rd_no:
            params.update({'rd_no': rd_no})
        if po_no:
            params.update({'po_no': po_no})
        if col_inv_no:
            params.update({'col_inv_no': col_inv_no})
        if inv_start_date and inv_end_date:
            params.update({
                'inv_start_date': inv_start_date,
                'inv_end_date': inv_end_date,
            })
        if product_code:
            params.update({'product_code': product_code})

        data.update({'records': records, 'parameters': params})
        res = {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': data,
        }
        return res
