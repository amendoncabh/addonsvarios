# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import codecs
import base64
from odoo import api, fields, models, tools, _
import datetime
from datetime import timedelta
from odoo.exceptions import ValidationError

tools.config['bank_transfer_dir'] = tools.config.get('bank_transfer_dir', '/home/jamesmie/Workspace/ofm/')
tools.config['bank_transfer_file_name'] = tools.config.get('bank_transfer_file_name', 'ofm_bank_transfer')


class ExportBankTransferWizard(models.TransientModel):
    _name = 'export.bank.transfer.wizard'

    from_branch_id = fields.Many2one(
        comodel_name="pos.branch",
        string="Store From",
        required=True,
        default=lambda self: self.env.user.branch_id,
    )

    to_branch_id = fields.Many2one(
        comodel_name="pos.branch",
        string="To",
        required=True,
        default=lambda self: self.env.user.branch_id,
    )

    sale_date = fields.Date(
        string="Sale Date",
        required=True,
        default=fields.Datetime.now,
    )

    bank = fields.Selection(
        string="Bank",
        selection=[
           ('kbank', 'KBANK'),
           ('scb', 'SCB'),
        ],
        required=True,
        default='kbank',
    )

    binary_data = fields.Binary(
        string="Download File",
        required=False,
    )

    filename = fields.Char(
        string="File Name",
        required=False,
    )

    def write_file_bank_transfer_kbank(self, detail):
        bank_transfer_dir = tools.config['bank_transfer_dir']
        date_now = datetime.datetime.now() + timedelta(hours=7)
        bank_transfer_file_name = ''.join([
            tools.config['bank_transfer_file_name'],
            '.txt',
        ])
        path = ''.join([
            bank_transfer_dir,
            bank_transfer_file_name,
        ])

        open_file = codecs.open(path, 'w+', encoding="cp1252")

        open_file.write(
            detail
        )

        open_file.close()

        data = open(path, "r").read()

        bank_transfer_file_name_for_download = ''.join([
            tools.config['bank_transfer_file_name'],
            date_now.strftime("_%Y%m%d_%H%M"),
            '.txt',
        ])

        self.write({
            'binary_data': base64.b64encode(data),
            'filename': bank_transfer_file_name_for_download,
        })

    @api.multi
    def action_export_bank_transfer(self):
        for item in self:
            if item.from_branch_id and item.to_branch_id:
                branch_ids = self.env['pos.branch'].search([('branch_code', '>=', item.from_branch_id.branch_code),
                                                            ('branch_code', '<=', item.to_branch_id.branch_code)])
                bank_thai = branch_ids.mapped('bank_id').mapped('bank_thai')
                if item.bank not in bank_thai:
                    raise ValidationError(_("ไม่พบ %s ใน Store Code : %s - %s") % (item.bank,
                                                                                item.from_branch_id.branch_code,
                                                                                item.to_branch_id.branch_code))
            if item.bank == 'kbank':
                parameter = (
                    item.sale_date,
                    item.from_branch_id.branch_code,
                    item.to_branch_id.branch_code,
                )

                item._cr.execute("""
                    update daily_summary_franchise
                    set last_export_date = now()
                    from (
                          select dsf.id as daily_summary_id
                          from (
                                select *
                                from daily_summary_franchise
                                /* Parameter */
                                where (date + interval '7 hours')::date = %s
                                      and state = 'active'
                               ) dsf
                          left join (
                                     select *
                                     from bank_transfer_status
                                     where code = '00'
                                    ) bts on dsf.bank_transfer_status_id = bts.id
                          inner join (
                                      select *
                                      from pos_branch
                                      /* Parameter */
                                      where branch_code between %s and %s
                                     ) pbr on dsf.branch_id = pbr.id
                          inner join res_partner_bank rpb on rpb.id = pbr.res_partner_bank_id
                          inner join (
                                      select *
                                      from res_bank
                                      where active is true
                                            and bank_thai = 'kbank'
                                     ) rbk on rpb.bank_id = rbk.id
                          where bts.id is null
                         ) m_dsf
                    where id = m_dsf.daily_summary_id
                """, parameter)

                item._cr.execute("""
                    WITH temp_bank_transfer AS 
                       (
                        select ROW_NUMBER () OVER (ORDER BY dsf.id) as trans_no,
                               '7441'::text || ' ' as trans_type,
                               lpad(com.company_code_account_fc, 7, ' ')::text || ' ' as company_code,
                               lpad(rpb.acc_number, 10, ' ') || ' ' as account_no,
                               lpad(
                                    REPLACE(
                                            round(dsf.sum_bank_transfer::numeric,2)::text, '.', ''
                                           ), 15, '0'
                                   ) || ' ' as amount,
                               to_char(now() + interval '7 hours', 'YYMMDD') as trans_date,
                               lpad(
                                   CONCAT(
                                       pbr.branch_code,to_char(dsf.date + interval '7 hours', 'YYMMDD')
                                       ), 23, ' '
                                    )  || ' ' as title,
                               lpad(rpb.acc_name_en, 50, ' ') as name,
                               round(dsf.sum_bank_transfer::numeric,2) as for_cal_amount
                        from ( 
                              select *
                              from daily_summary_franchise
                              /* Parameter */
                              where (date + interval '7 hours')::date = %s
                                    and state = 'active'
                             ) dsf
                        left join (
                                   select *
                                   from bank_transfer_status
                                   where code = '00'
                                  ) bts on dsf.bank_transfer_status_id = bts.id
                        inner join (
                                    select *
                                    from pos_branch
                                    /* Parameter */
                                    where branch_code between %s and %s
                                   ) pbr on dsf.branch_id = pbr.id
                        inner join res_partner_bank rpb on rpb.id = pbr.res_partner_bank_id
                        inner join res_company com on rpb.company_id = com.id
                        inner join (
                                    select *
                                    from res_bank
                                    where active is true
                                    and bank_thai = 'kbank'
                                   ) rbk on rpb.bank_id = rbk.id
                        cross join (
                                    select *
                                    FROM ir_config_parameter
                                    WHERE key = 'company_code'
                                   ) icp
                        where bts.id is null
                       )
    
                    select concat(
                                  trans_no,
                                  trans_type,
                                  company_code,
                                  account_no,
                                  amount,
                                  trans_date,
                                  title,
                                  name
                                 ) transfer_data
                    from (
                          select lpad(trans_no::text, 6, '0') || ' ' as trans_no,
                                 trans_type,
                                 company_code,
                                 account_no,
                                 amount,
                                 (trans_date || ' ') as trans_date,
                                 title,
                                 (COALESCE(name,'') || '\r\n'::text)  as name
                          from temp_bank_transfer
                          union
                          select lpad((Max(trans_no) + 1)::text, 6, '0') || ' ' as trans_no,
                                 '9100'::text || ' ' as trans_type,
                                 company_code as company_code,
                                 '0000000000'::text || ' ' as account_no,
                                 lpad(
                                      REPLACE(
                                              sum(round(for_cal_amount::numeric,2))::text, '.', ''
                                             ), 15, '0'
                                     ) || ' ' as amount,
                                 '000000'::text as trans_date,
                                 ''::text,
                                 ''::text
                          from temp_bank_transfer
                          group by company_code,
                                   trans_date
                         ) result
                    order by trans_no
                                        """, parameter)

                daily_bank_transfer_kbank_list = item._cr.dictfetchall()
                if daily_bank_transfer_kbank_list == []:
                    raise ValidationError(_("No Data"))
                detail = ''
                for daily_bank_transfer in daily_bank_transfer_kbank_list:
                    detail += daily_bank_transfer['transfer_data']
                item.write_file_bank_transfer_kbank(detail)

                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'export.bank.transfer.wizard',
                    'view_mode': 'form',
                    'view_type': 'form',
                    'res_id': item.id,
                    'views': [(False, 'form')],
                    'target': 'new',
                }
