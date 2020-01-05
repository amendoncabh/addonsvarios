# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
import datetime
import logging

_logger = logging.getLogger(__name__)

class DailySummaryFranchise(models.Model):
    _name = "daily.summary.franchise"
    _inherit = ['mail.thread']
    _order = 'date desc, id desc'
    _rec_name = 'date'

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        index=True,
        readonly=True,
    )

    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        required=True,
        index=True,
        readonly=True,
        related='company_id.currency_id',
        track_visibility='always',
    )

    user_id = fields.Many2one(
        comodel_name='res.users',
        string='Salesperson',
        index=True,
        track_visibility='onchange',
        default=lambda self: self.env.user,
    )
    
    date = fields.Date(
        string="Date",
        required=True,
        readonly=True,
    )

    branch_id = fields.Many2one(
        comodel_name="pos.branch",
        string="Branch",
        required=True,
        index=True,
        readonly=True,
    )

    state = fields.Selection(
        string="State",
        selection=[
            ('draft', 'Draft'),
            ('verify', 'Confirm'),
            ('active', 'Active'),
            ('cancel', 'Cancelled'),
        ],
        required=True,
        default='draft',
        readonly=True,
    )

    bank_transfer_status_id = fields.Many2one(
        comodel_name="bank.transfer.status",
        string="Bank Transfer Status",
        required=False,
        readonly=True,
    )

    store_code = fields.Char(
        string="Store Code",
        required=True,
        readonly=True,
    )

    store_name = fields.Char(
        string="Store Name",
        required=False,
        readonly=True,
    )

    last_export_date = fields.Datetime(
        string="Last Export Date",
        required=False,
        readonly=True,
    )

    last_import_date = fields.Datetime(
        string="Last Import Date",
        required=False,
        readonly=True,
    )

    sum_sub_total = fields.Float(
        string="Sub Total",
        required=False,
        readonly=True,
        compute="_sum_amount_all",
        store=True,
    )

    sum_discount_by_sor = fields.Float(
        string="Discount by Sor",
        required=False,
        readonly=True,
        compute="_sum_amount_all",
        store=True,
    )

    sum_discount_by_see = fields.Float(
        string="Discount by See",
        required=False,
        readonly=True,
        compute="_sum_amount_all",
        store=True,
    )

    sum_delivery_fee = fields.Float(
        string="Delivery Fee",
        required=False,
        readonly=True,
        compute="_sum_amount_all",
        store=True,
    )

    sum_total = fields.Float(
        string="Total",
        required=False,
        readonly=True,
        compute="_sum_amount_all",
        store=True,
    )

    sum_bank_transfer = fields.Float(
        string="Bank Transfer",
        required=False,
        readonly=True,
        compute="_sum_amount_all",
        store=True,
    )

    sum_cash_total = fields.Float(
        string="Total",
        required=False,
        readonly=True,
        compute="_sum_amount_cash",
        store=True,
    )

    daily_summary_franchise_line_ids = fields.One2many(
        comodel_name="daily.summary.franchise.line",
        inverse_name="daily_summary_franchise_id",
        string="Detail",
        required=False,
    )

    daily_summary_franchise_credit_term_ids = fields.One2many(
        comodel_name="daily.summary.franchise.credit.term",
        inverse_name="daily_summary_franchise_id",
        string="ตารางสรุปยอดชำระเงิน Credit Term",
        required=False,
    )

    daily_summary_franchise_cash_ids = fields.One2many(
        comodel_name="daily.summary.franchise.cash",
        inverse_name="daily_summary_franchise_id",
        string="Summary Cash",
        required=False,
    )

    is_backdate = fields.Boolean(
        string="Is Backdate",
        default=False,
    )

    reason = fields.Char(
        string="Reason",
    )

    @api.model
    def get_can_edit(self):
        flag = self.env.user.has_group('ofm_access_right_center.group_ofm_hq')
        return flag

    @api.onchange('is_backdate')
    def _onchange_is_backdate(self):
        if self.is_backdate == True:
            dsf_ids = self.search([
                                    ('state', '!=', 'cancel'),
                                    ('is_backdate','=', True),
                                    ('branch_id', '=', self.branch_id.id)])
            if len(dsf_ids) >= 1:
                self.is_backdate = False
                return {'warning': {
                    'title': "Warning",
                    'message': "มีใบสรุปประจำวันของสาขา"+self.branch_id.name+" ย้อนหลังแล้ว 1 ใบ\nสามารถมีได้ 1 ใบ/สาขา เท่านั้น",
                    }
                }

    @api.multi
    def name_get(self):
        result = []
        for record in self:
            name = ''.join([
                record.store_name,
                ' ',
                datetime.datetime.strptime(record.date, "%Y-%m-%d").strftime("%d/%m/%Y"),
            ])

            result.append((record.id, name))

        return result

    @api.multi
    @api.depends('daily_summary_franchise_line_ids.sub_total',
                 'daily_summary_franchise_line_ids.discount_by_sor',
                 'daily_summary_franchise_line_ids.discount_by_see',
                 'daily_summary_franchise_line_ids.delivery_fee',
                 'daily_summary_franchise_line_ids.total',
                 'daily_summary_franchise_line_ids.bank_transfer',)
    def _sum_amount_all(self):
        sum_sub_total = 0.0
        sum_discount_by_sor = 0.0
        sum_discount_by_see = 0.0
        sum_delivery_fee = 0.0
        sum_total = 0.0
        sum_bank_transfer = 0.0

        for item in self:
            for line in item.daily_summary_franchise_line_ids:
                sum_sub_total += line.sub_total
                sum_discount_by_sor += line.discount_by_sor
                sum_discount_by_see += line.discount_by_see
                sum_delivery_fee += line.delivery_fee
                sum_total += line.total
                sum_bank_transfer += line.bank_transfer

            item.update({
                'sum_sub_total': sum_sub_total,
                'sum_discount_by_sor':  sum_discount_by_sor,
                'sum_discount_by_see':  sum_discount_by_see,
                'sum_delivery_fee': sum_delivery_fee,
                'sum_total': sum_total,
                'sum_bank_transfer': sum_bank_transfer,
            })

    @api.multi
    @api.depends('daily_summary_franchise_cash_ids.total',)
    def _sum_amount_cash(self):
        sum_cash_total = 0.0

        for item in self:
            for line in item.daily_summary_franchise_cash_ids:
                sum_cash_total += line.total

            item.update({
                'sum_cash_total': sum_cash_total,
            })

    @api.multi
    def action_cancel(self):
        for item in self:
            parameter_update_pos_so = (
                item.id,
                item.id,
                item.id,
            )

            item._cr.execute("""
                /* Update POS */

                update pos_order
                set daily_summary_franchise_id = null
                /* Parameter */
                where daily_summary_franchise_id = %s;

                /* Update SO */

                update sale_order
                set daily_summary_franchise_id = null
                where daily_summary_franchise_id = %s;

                /* Update INV */

                update account_invoice
                set daily_summary_franchise_id = null
                where daily_summary_franchise_id = %s;
                """, parameter_update_pos_so)

            return item.write({'state': 'cancel'})

    @api.multi
    def action_confirm(self):
        return self.write({'state': 'active'})

    @api.multi
    def action_verify(self):
        return self.write({'state': 'verify'})

    def update_daily_summary_franchise_by_cron(self):
        cal_daily_summary_franchise_wizard_obj = self.env['cal.daily.summary.franchise.wizard']
        branch_ids = self.env['pos.branch'].search([])

        for branch in branch_ids:
            if branch.is_cron_job == True:
                new_cal_daily_summary_franchise_wizard_obj = cal_daily_summary_franchise_wizard_obj.create({
                    'date': fields.Date.today(),
                    'pos_cash': 0.00,
                    'so_cash': 0.00,
                    'credit_term': 0.00,
                    'branch_id': branch.id,
                    'manager_id': self.env.user.id,
                    'manager_pin': '0',
                    'kerry_cash': 0.00,
                    'is_auto_cal': True,
                })

                new_cal_daily_summary_franchise_wizard_obj.action_cal_daily_summary_franchise()

                _logger.info("Start create daily summary cal_franchise Branch ID :%s Date: %s ",
                             branch.id, fields.Date.today())

    @api.multi
    def write(self, values):
        masege_obj = self.env['mail.message']
        body = ''
        for vals_key in values:
            if vals_key == 'daily_summary_franchise_line_ids':
                modle = 'daily.summary.franchise.line'
                menu_name = 'Detail'
            elif vals_key == 'daily_summary_franchise_credit_term_ids':
                modle = 'daily.summary.franchise.credit.term'
                menu_name = 'ตารางสรุปยอดชำระเงิน Credit Term'
            elif vals_key == 'daily_summary_franchise_cash_ids':
                modle = 'daily.summary.franchise.cash'
                menu_name = 'Summary Cash'
            else:
                continue
            body += menu_name + '<br>'
            for daily_fc_vals in values.get(vals_key):
                if daily_fc_vals[2] != False:
                    daily_fc_id = self.env[modle].search(
                        [('id', '=', daily_fc_vals[1]), ])
                    if daily_fc_id:
                        if menu_name == 'Detail':
                            name = daily_fc_id.session_no_and_so
                        else:
                            name = daily_fc_id.name
                        body += "<ul class=''><li>" + name + ' : '
                        for key in daily_fc_vals[2]:
                            key = str(key)
                            body += key + " : ( " + str(daily_fc_id.mapped(key)[0]) + "--->" + str(
                                daily_fc_vals[2][key]) + " ) "
                        body += "</li></ul>"
        body = "<div style='background-color: rgb(228 ,228 ,228);'>{}</div>".format(body)
        message_qty_before = len(masege_obj.search
                                  ([('model', '=', 'daily.summary.franchise'),('res_id', '=', self.id)]))
        result = super(DailySummaryFranchise, self).write(values)
        message_qty_after = len(masege_obj.search
                                  ([('model', '=', 'daily.summary.franchise'), ('res_id', '=', self.id)]))
        if message_qty_before != message_qty_after:
            masege_id = masege_obj.search([
            ('model', '=', 'daily.summary.franchise'),
            ('res_id', '=', self.id), ], limit=1)
            masege_id.write({'body': body})
        else:
            messg_vals = {
                    'model': 'daily.summary.franchise',
                    'res_id': self.id,
                    'parent_id': False,
                    'body': body,
                    'date': datetime.datetime.now()
                }
            masege_obj.create(messg_vals)
        return result

    def edit_daily_summary_franchise(self):
        pos_cash = so_cash = credit_term = kerry_cash = 0
        for cash in self.daily_summary_franchise_cash_ids:
            if cash.name == 'Cash (POS)':
                pos_cash += cash.total
            if cash.name == 'Cash (Sale Order)':
                so_cash += cash.total
            if cash.name == 'ยอดรับชำระเครดิตเทอม':
                credit_term += cash.total
            if cash.name == 'Cash (Kerry)':
                kerry_cash += cash.total

        view = self.env.ref('ofm_franchise.view_edit_daily_summary_franchise_wizard')
        return {
            'name' : 'แก้ไขรายการสรุปยอดประจำวัน',
            'type' : 'ir.actions.act_window',
            'res_model' : 'cal.daily.summary.franchise.wizard',
            'view_type' : 'form',
            'view_mode' : 'form',
            'view_id' : view.id,
            'context' : {'default_date': self.date,
                        'default_branch_id': self.branch_id.id,
                        'default_pos_cash': pos_cash,
                        'default_so_cash': so_cash,
                        'default_credit_term': credit_term,
                        'default_kerry_cash': kerry_cash,},
            'target' : 'new',
        }


class DailySummaryFranchiseLine(models.Model):
    _name = "daily.summary.franchise.line"

    daily_summary_franchise_id = fields.Many2one(
        comodel_name="daily.summary.franchise",
        string="Daily Summary Franchise",
        required=True,
        index=True,
        ondelete="cascade",
    )

    is_pos = fields.Boolean(
        string="",
        default=False,
    )

    is_so = fields.Boolean(
        string="",
        default=False,
    )

    session_no_and_so = fields.Char(
        string="Session No. / Sale Order",
        required=True,
        readonly=True,
    )

    sub_total = fields.Float(
        string="Sub Total",
        required=False,
    )

    discount_by_sor = fields.Float(
        string="Discount by Sor",
        required=False,
    )

    discount_by_see = fields.Float(
        string="Discount by See",
        required=False,
    )

    delivery_fee = fields.Float(
        string="Delivery Fee",
        required=False,
    )

    total = fields.Float(
        string="Total",
        required=False,
    )

    bank_transfer = fields.Float(
        string="Bank Transfer",
        required=False,
    )


class DailySummaryFranchiseCreditTerm(models.Model):
    _name = "daily.summary.franchise.credit.term"

    daily_summary_franchise_id = fields.Many2one(
        comodel_name="daily.summary.franchise",
        string="Daily Summary Franchise",
        required=True,
        index=True,
        ondelete="cascade",
    )

    name = fields.Char(
        string="Detail",
        required=True,
    )

    total = fields.Float(
        string="Total",
        required=False,
    )


class DailySummaryFranchiseCash(models.Model):
    _name = "daily.summary.franchise.cash"

    daily_summary_franchise_id = fields.Many2one(
        comodel_name="daily.summary.franchise",
        string="Daily Summary Franchise",
        required=True,
        index=True,
        ondelete="cascade",
    )

    name = fields.Char(
        string="Detail",
        required=True,
        readonly=True,
    )

    total = fields.Float(
        string="Total",
        required=False,
    )
