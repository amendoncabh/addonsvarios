# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from StringIO import StringIO


class ConfirmMonthlySummaryFranchise(models.TransientModel):
    _name = 'confirm.monthly.summary.franchise'
    _description = "Confirm Monthly Summary Franchise"

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
        default='05',
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
        default='2019',
    )

    branch_ids = fields.Many2many(
        comodel_name="pos.branch",
        string="Store",
    )

    @api.multi
    def action_confirm(self):
        month_sum_fran_obj = self.env['monthly.summary.franchise']
        for item in self:
            domain = []
            vals = [
                ('month', '=', item.month),
                ('year', '=', item.year),
                ('state', '=', 'draft'),
            ]
            if item.branch_ids:
                vals += [('branch_id', 'in', item.branch_ids.ids)]
                domain += [('branch_id', 'in', item.branch_ids.ids)]
            month_sum_fran_ids = month_sum_fran_obj.search(vals)
            for month_sum_fran_id in month_sum_fran_ids:
                month_sum_fran_id.action_in_process()
            domain += [
                ('month', '=', item.month),
                ('year', '=', item.year),
                ('state', '=', 'in_process')
            ]
        return {
            'view_type': 'form',
            'view_mode': 'tree,form',
            'name': 'ใบสรุปประจำเดือน',
            'res_model': 'monthly.summary.franchise',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': domain,
        }

    @api.multi
    def action_set_to_draft(self):
        month_sum_fran_obj = self.env['monthly.summary.franchise']
        for item in self:
            domain = []
            vals = [
                ('month', '=', item.month),
                ('year', '=', item.year),
                ('state', '=', 'in_process')
            ]
            if item.branch_ids:
                vals += [('branch_id', 'in', item.branch_ids.ids)]
                domain += [('branch_id', 'in', item.branch_ids.ids)]
            month_sum_fran_ids = month_sum_fran_obj.search(vals)
            for month_sum_fran_id in month_sum_fran_ids:
                month_sum_fran_id.action_draft()
            domain += [
                ('month', '=', item.month),
                ('year', '=', item.year),
                ('state', '=', 'draft')
            ]
        return {
            'view_type': 'form',
            'view_mode': 'tree,form',
            'name': 'ใบสรุปประจำเดือน',
            'res_model': 'monthly.summary.franchise',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': domain,
        }
