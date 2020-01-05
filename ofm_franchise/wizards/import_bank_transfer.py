# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from StringIO import StringIO
import datetime
from odoo.exceptions import ValidationError

class ImportBankTransfer(models.TransientModel):
    _name = 'import.bank.transfer.wizard'
    _description = "Import Bank Transfer"

    binary_data = fields.Binary(
        string="File",
        required=True,
    )

    filename = fields.Char(
        string="File Name",
        required=False,
    )

    @api.multi
    def action_import_bank_transfer(self):
        dsf_ids = []
        for item in self:
            data = StringIO(item.binary_data.decode('base64'))
            bank_transfer_data = data.read()
            bank_transfer_data_list = bank_transfer_data.split('\n')
            for bank_transfer in bank_transfer_data_list:
                if bank_transfer[7:11] == '7441':
                    try:
                        branch_id = item.env['pos.branch'].search([
                            ('branch_code', '=', bank_transfer[65:71])
                        ], order="id desc", limit=1).id
                        if branch_id == False:
                            raise Exception(
                                    "Acconut Number : %s\nไม่พบ Branch จาก partner bank " % bank_transfer[65:71])
                        kbank_status_id = item.env['bank.transfer.status'].search([
                            ('code', '=', bank_transfer[54:56]),
                            ('bank', '=', 'kbank'),
                        ], order="id desc", limit=1).id
                        if kbank_status_id == False:
                            raise Exception(
                                    "Bank Status Code : %s\nไม่พบ Bank Status " % bank_transfer[54:56])
                        trans_date = datetime.datetime.strptime(bank_transfer[71:77], "%y%m%d").strftime("%Y/%m/%d")

                        parameter = (
                            kbank_status_id,
                            branch_id,
                            trans_date,
                        )
                        item._cr.execute("""
                            update daily_summary_franchise
                            set bank_transfer_status_id = %s,
                                last_import_date = now()
                            where state = 'active'
                                and branch_id = %s
                                and date = %s
                        """, parameter)
                        item._cr.execute("""
                            SELECT id
                            FROM daily_summary_franchise
                            where state = 'active'
                                and bank_transfer_status_id = %s
                                and branch_id = %s
                                and date = %s
                        """, parameter)
                        dsf_id = item._cr.fetchall()
                        for dsf_id in dsf_id[0]:
                            dsf_ids.append(dsf_id)
                    except Exception as e:
                        raise ValidationError(
                            "Import Unsuccessful!!!!\n\n%s." % e.message)
        return {
            'view_type': 'form',
            'view_mode': 'tree,form',
            'name': 'ใบสรุปประจำวัน',
            'res_model': 'daily.summary.franchise',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', dsf_ids)],
        }
