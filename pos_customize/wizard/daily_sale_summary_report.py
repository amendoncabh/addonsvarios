# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

__author__ = 'Papatpon'

class DailySaleSummaryReport(models.TransientModel):
    _name = 'daily.sale.summary.report.wizard'
    _description = "Daily Sale Summary Report"

    start_date = fields.Date(
        string='Start Date',
        default=fields.Datetime.now,
    )
    end_date = fields.Date(
        string='End Date',
        default=fields.Datetime.now,
    )

    start_branch = fields.Many2one(
        'pos.branch',
        string='Start Branch'
    )
    end_branch = fields.Many2one(
        'pos.branch',
        string='End Branch'
    )
    jasper_output = fields.Selection(
        [
             ('xls', '.Excel'),
             ('pdf', '.PDF'),
        ],
         string = 'Report Type'
    )

    @api.multi
    def action_print_report(self, data):
        records = []
        report_name = "daily.sale.summary.report.jasper"
        wizard = self
        start_date = wizard.start_date
        end_date = wizard.end_date
        start_branch = wizard.start_branch.sequence
        end_branch = wizard.end_branch.sequence
        jasper_output = wizard.jasper_output

        # ir_model_report_id = self.pool.get('ir.model.data')
        # model_data_id = ir_model_report_id._get_id(cr, uid, 'pos_customize', 'net_sale_by_categories_report_jasper')
        # net_sale_by_categories_id   = ir_model_report_id.read(cr, 1, [model_data_id], ['res_id'])[0]['res_id']
        # net_sale_by_categories_name = self.pool.get('ir.actions.report.xml').browse(cr, uid, net_sale_by_categories_id, context)

        daily_sale_summary_report = self.env.ref('pos_customize.daily_sale_summary_report_jasper')

        daily_sale_summary_report.write({
           'jasper_output' : jasper_output,
        })

        #Send parameter to print
        params = {
            'start_date': start_date,
            'end_date': end_date,
            'start_branch': str(start_branch),
            'end_branch': str(end_branch),
        }
        data.update({'records': records, 'parameters': params})
        res = {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': data,
        }
        return res
