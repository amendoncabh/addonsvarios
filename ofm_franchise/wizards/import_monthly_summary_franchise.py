# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from StringIO import StringIO
from odoo import api, fields, models
from odoo.exceptions import ValidationError, UserError
from pandas import ExcelFile
import math


class ImportMonthlySummaryFranchise(models.TransientModel):
    _name = 'import.monthly.summary.franchise'
    _description = "Import Monthly Summary Franchise"

    binary_data = fields.Binary(
        string="XLS File",
        required=True,
    )

    filename = fields.Char(
        string="File Name",
        required=False,
    )

    @api.multi
    def action_import_monthly_summary_franchises(self):
        for item in self:
            list_msf_ids = []
            franchise = {}
            coa_obj = item.env['monthly.summary.franchise.coa']
            data = StringIO(item.binary_data.decode('base64'))
            try:
                xls = ExcelFile(data)
                sheets = xls.sheet_names

            except Exception as e:
                raise UserError(
                    "Import Unsuccessful!!!!\n\nReason : %s." % e.message)
            for sheet in sheets:
                data = xls.parse(sheet)
                monthly_sum_fran = data.to_dict()
                xls_col = [x for x in monthly_sum_fran]
                if xls_col == []:
                    raise ValidationError("Sheet Name : %s --> No Data\nกรุณาตรวจสอบไฟล์และทำการ Import ใหม่อีกครั้ง" % sheet)
                for running in range(0, len(monthly_sum_fran[xls_col[0]])):
                    try:
                        store_code = str(monthly_sum_fran['StoreCode'][running])
                        store_code = '0' + store_code if len(store_code) < 6 else store_code
                        wht_amount = monthly_sum_fran['WHTax Amount'][running]
                        vat_amount = monthly_sum_fran['VAT Amount'][running]
                        code = float(monthly_sum_fran['Sub Group'][running])
                        whtax_to = monthly_sum_fran['WHTax To'][running]
                        month = str(monthly_sum_fran['Month'][running])
                        month = '0'+month if len(month) < 2 else month
                        group_name = monthly_sum_fran['GroupName'][running]
                        amount = monthly_sum_fran['Amount'][running]
                        year = str(monthly_sum_fran['Year'][running])
                        whtax_from = monthly_sum_fran['WHTax From'][running]
                        amount_total = monthly_sum_fran['Total'][running]
                    except Exception as e:
                        raise UserError(
                            "Import Unsuccessful!!!!\n\nReason : Column name '%s' cannot be found." % e.message)
                    msf_name = str(year[2:4]) + str(month) + str(store_code)
                    if item._context.get('many_store') == True:
                        coa_id = coa_obj.search([
                            ('number', '=', code),
                            ('monthly_summary_franchise_id.store_code', '=', store_code),
                            ('monthly_summary_franchise_id.month', '=', month),
                            ('monthly_summary_franchise_id.year', '=', year)])
                        msf_id = coa_id.monthly_summary_franchise_id.id
                        if msf_id not in list_msf_ids and coa_id.state == 'draft':
                            list_msf_ids.append(msf_id)
                        if not coa_id:
                            raise TypeError(
                                "ไม่พบใบสรุปประจำเดือน \nกรุณาคำนวณสรุปยอดประจำเดือน : 'FR" + msf_name + "' ก่อน")
                    else:
                        msf_id = item._context['active_id']
                        coa_id = coa_obj.search([
                            ('number', '=', code),
                            ('monthly_summary_franchise_id.store_code', '=', store_code),
                            ('monthly_summary_franchise_id.month', '=', month),
                            ('monthly_summary_franchise_id.year', '=', year),
                            ('monthly_summary_franchise_id', '=', msf_id)])
                        if coa_id:
                            list_msf_ids.append(msf_id)

                    if coa_id:
                        sub_group = {str(code): {
                            'store_code': store_code,
                            'month': month,
                            'year': year,
                            'number': code,
                            'group_name': group_name,
                            'amount': amount if not math.isnan(amount) else 0.0,
                            'vat_amount': vat_amount if not math.isnan(vat_amount) else 0.0,
                            'wht_amount': wht_amount if not math.isnan(wht_amount) else 0.0,
                            'amount_total': amount_total if not math.isnan(amount_total) else 0.0,
                            'whtax_from': whtax_from.lower() if str(whtax_from) != 'nan' else 'see',
                            'whtax_to': whtax_to.lower() if str(whtax_to) != 'nan' else 'see',
                            'amount_original': amount_total if not math.isnan(amount_total) else 0.0,
                            'coa_id': coa_id,
                        }}
                        store = {msf_name: sub_group, }
                        if coa_id.state == 'draft':
                            if msf_name not in franchise:
                                franchise.update(store)
                            else:
                                if str(code) not in franchise[msf_name]:
                                    franchise[msf_name].update(sub_group)
                                else:
                                    line = franchise[msf_name][str(code)]
                                    line['amount'] = amount
                                    line['vat_amount'] = vat_amount
                                    line['wht_amount'] = wht_amount
                                    line['amount_total'] = amount_total
                                    line['amount_original'] = amount_total

            for key, value in franchise.iteritems():
                for k, vals in value.iteritems():
                    vals['coa_id'].update({
                        'amount': vals['amount'],
                        'vat_amount': vals['vat_amount'],
                        'wht_amount': vals['wht_amount'],
                        'amount_total': vals['amount_total'],
                        'amount_original': vals['amount_total'],
                        'coa_from': vals['whtax_from'],
                        'coa_to': vals['whtax_to']
                    })
        return {
            'view_type': 'form',
            'view_mode': 'tree,form',
            'name': 'ใบสรุปประจำเดือน',
            'res_model': 'monthly.summary.franchise',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': [('id', 'in', list_msf_ids)],
        }

    @api.multi
    def action_upload_file_attachment(self):
        attachment_obj = self.env['ir.attachment']
        for item in self:
            context = item._context
            if context:
                active_model = context['active_model']
                active_id = context['active_id']
                attachments = attachment_obj.search([
                    ('res_model', '=', active_model),
                    ('res_id', '=', active_id),
                    ('datas_fname', '=', item.filename)
                ])
                if not attachments:
                    attachment_obj.create({
                        'name': item.filename,
                        'res_model': active_model,
                        'res_id': active_id,
                        'datas': item.binary_data,
                        'datas_fname': item.filename,
                    })
                else:
                    raise ValidationError("Sorry, you can't upload this file again.")
