# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class POShipDateReport(models.TransientModel):
    _name = 'po.ship.date.report.wizard'
    _description = "PO Ship Date Report"

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

    planned_start_date = fields.Date(
        string='Due Start Date',
        default=fields.Datetime.now,
        required=True,
    )

    planned_end_date = fields.Date(
        string='Due End Date',
        default=fields.Datetime.now,
        required=True,
    )

    po_start_date = fields.Date(
        string='PO Start Date',
        required=False,
    )

    po_end_date = fields.Date(
        string='PO End Date',
        required=False,
    )

    pr_start_date = fields.Date(
        string='PR Start Date',
        required=False,
    )

    pr_end_date = fields.Date(
        string='PR End Date',
        required=False,
    )

    inv_col_no = fields.Char(
        string="Invoice COL No.",
        required=False,
    )

    vendor_code_branch = fields.Char(
        string="Vendor",
        required=False,
    )

    product_pid_sku = fields.Char(
        string="Product",
        required=False,
    )

    po_status = fields.Many2many(
        'po.status',
        string='PO Status',
        required=True,
        domain=[('value', '<>', 'draft'),
                ('value', '<>', 'sent')]
    )

    stock_received = fields.Selection(
        string='Shipment Received',
        selection=[
            ('assigned', 'Available'),
            ('done', 'Done')
        ],
    )

    @api.multi
    def action_print_report(self, data):
        records = []
        report_name = "po.ship.date.report.jasper"
        wizard = self

        if not wizard.po_status:
            raise UserError(_('Please check field PO Status before print report'))

        company_id = wizard.company_id.id
        branch_id = wizard.branch_id.id
        planned_start_date = wizard.planned_start_date
        planned_end_date = wizard.planned_end_date
        po_start_date = wizard.po_start_date
        po_end_date = wizard.po_end_date
        pr_start_date = wizard.pr_start_date
        pr_end_date = wizard.pr_end_date
        inv_col_no = wizard.inv_col_no
        vendor_code_branch = wizard.vendor_code_branch
        product_pid_sku = wizard.product_pid_sku

        po_status = ''
        for item in wizard.po_status:
            po_status += str(',' + item.value + ',')

        stock_received = ''
        if wizard.stock_received:
            stock_received = str(wizard.stock_received)

        # Send parameter to print
        params = {
            'company_id': str(company_id),
            'branch_id': str(branch_id),
            'planned_start_date': planned_start_date,
            'planned_end_date': planned_end_date,
            'po_status': po_status,
            'stock_received': stock_received,
        }

        if po_start_date and po_end_date:
            params.update({
                'po_start_date': po_start_date,
                'po_end_date': po_end_date,
            })

        if pr_start_date and pr_end_date:
            params.update({
                'pr_start_date': pr_start_date,
                'pr_end_date': pr_end_date,
            })

        if inv_col_no:
            params.update({'inv_col_no': inv_col_no})

        if vendor_code_branch:
            params.update({'vendor_code_branch': vendor_code_branch})

        if product_pid_sku:
            params.update({'product_pid_sku': product_pid_sku})

        data.update({'records': records, 'parameters': params})
        res = {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': data,
        }
        return res
