# -*- coding: tis-620 -*-

import logging
import os
import codecs
from datetime import datetime
from pytz import timezone

from odoo import models, fields, api, tools

_logger = logging.getLogger(__name__)

# mapping invoice type to journal type
TYPE2JOURNAL = {
    'out_invoice': 'sale',
    'in_invoice': 'purchase',
    'out_refund': 'sale',
    'in_refund': 'purchase',
}

# mapping invoice type to refund type
TYPE2REFUND = {
    'out_invoice': 'out_refund',  # Customer Invoice
    'in_invoice': 'in_refund',  # Vendor Bill
    'out_refund': 'out_invoice',  # Customer Refund
    'in_refund': 'in_invoice',  # Vendor Refund
}


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    is_get_data_already = fields.Boolean(
        'Interface Already',
        copy=False,
        readonly=True,
        default=False,
    )

    def write_file_ofin(self, path, detail, file_type):
        ofin_dir = tools.config['ofin_dir']
        path = ''.join([
            ofin_dir,
            path
        ])
        exists = os.path.isfile(path)
        num_lines = 0
        if exists and file_type != 'log':
            with codecs.open(path, 'r', encoding="tis-620") as f:
                for line in f:
                    num_lines += 1

            open_file = codecs.open(path, 'a+', encoding="tis-620")
            open_file.write(
                detail
            )

        elif exists and file_type == 'log':
            open_file = codecs.open(path, 'r+', encoding="tis-620")
            open_file.write(
                detail
            )

        else:
            open_file = codecs.open(path, 'w+', encoding="tis-620")
            open_file.write(
                detail
            )
            open_file.close()

        return num_lines

    def put_blank_string(self, value):
        if isinstance(value, str) and 'blank' in value:
            values = value.split('_')
            values[0] = ''
            for i in range(int(values[1])):
                values[0] += ' '
            return values[0]
        else:
            return value

    def prepare_data_for_compare_amount_of_data(self, model, now_query_str):
        params = (
            model,
            now_query_str,
        )

        query_str = '''
                select 
                    res_id, max(log_amount), branch_code
                from
                    ofin_log_data_to_file logs
                where 
                    res_model = '%s'
                    and date_log_transaction = '%s'
                    group by res_id,branch_code
                ''' % params

        self.env.cr.execute(query_str)
        logs_invoice_this_day = self.env.cr.fetchall()

        group_res_id_branch = {}
        res_id_log_amount = {}

        for log_invoice_this_day in logs_invoice_this_day:
            if group_res_id_branch.get(log_invoice_this_day[2], False):
                group_res_id_branch[log_invoice_this_day[2]].append(
                    log_invoice_this_day[0]
                )
            else:
                group_res_id_branch.update({
                    log_invoice_this_day[2]: [log_invoice_this_day[0]]
                })

            res_id_log_amount.update({
                log_invoice_this_day[0]: log_invoice_this_day[1]
            })

        return group_res_id_branch, res_id_log_amount

    @api.multi
    def interface_invoice_ofin(self):
        for record in self:
            record.env['account.move'].with_context(
                franchise_invoice_id=record.id
            ).create_vendor_invoice_to_sor()

            return True

    @api.multi
    def interface_invoice_ap_ofin_to_file(self):
        for record in self:
            record.get_data_ap_to_generate_ofin_file()
            return True

    def get_data_ap_to_generate_ofin_file(self, invoice_id_query=''):

        ofin_log_data_obj = self.env['ofin.log.data.to.file']
        tr_convert = self.env['tr.convert']

        now_utc = tr_convert.convert_datetime_to_bangkok(datetime.now(timezone('UTC')))
        now_to_str = ''.join([
            '{:02d}'.format(now_utc.year),
            '{:02d}'.format(now_utc.month),
            '{:02d}'.format(now_utc.day)
        ])

        # if len(invoice_id_query):
        #     invoice_id_query = 'and aci.id = %s' % invoice_id_query

        query_str = '''
        select 
            aci.id as invoice_id,
            'ODO' as source,
            COALESCE(aci.reference, ' ') as invoice_number,
            COALESCE(
                rp.partner_code, 
                'F00000'
            ) as vendor_code,
            COALESCE(
                TO_CHAR(aci.vendor_invoice_date::date, 'DDMMYY')
                ,TO_CHAR((now() + interval '7 hours')::date, 'DDMMYY')
            ) as vendor_invoice_date,
            case
            when aci.type = 'in_invoice' then aci.amount_total
            when aci.type = 'in_refund' then aci.amount_total * -1
            end as amount_total,
            posb.branch_code,
            1 as invoice_type,
            'N' as import_good,
            'blank_2' as hold_reason,
            case
            when aci.amount_tax = 0 or rc.parent_company_id is null then '00.00'
            else '07.00' 
            end as invoice_tax_name,
            REPLACE(
                REPLACE(
                    REPLACE(aci.number, 'AP-0', '')
                ,'RTV-', '')
            ,'RT-', '')  as tax_inv_no,
            'blank_50' as tempolary_field,
            'blank_10' as rtv_auth_no,
            'THB' as currency_code,
            case 
            when apt.id is not null then LPAD(aptl.days::text, 4, '0')
            else '0000'
            end as term_payment,
            'blank_2' as tempolary_field_2,
            REPLACE(
                REPLACE(
                    REPLACE(aci.number, 'AP-0', '')
                ,'RTV-', '')
            ,'RT-', '') as gr_tran_no,
            case 
            when aci.type = 'in_refund' then REPLACE(
                REPLACE(
                    REPLACE(aci.number, 'AP-0', '')
                ,'RTV-', '')
            ,'RT-', '')
            else 'blank_50'
            end as ass_tax_invoice_num,
            'blank_14' as tempolary_field_3,
            TO_CHAR(aci.date_invoice::date, 'DDMMYY') as tax_invoice_date,
            TO_CHAR(aci.date_invoice::date, 'YYYYMMDD') as file_date,
            'blank_10' as invoice_rtv_type,
            'blank_50' as currency_rate,
            'blank_6' as due_date,
            aci.amount_tax,
            split_part(aci.origin, '-', 2) as origin_invoice

        from
            account_invoice aci
            inner join pos_branch posb on posb.id = aci.branch_id
            inner join res_partner rp on rp.id = aci.partner_id
            inner join res_company rc on rc.id = aci.company_id
            left join account_payment_term apt on apt.id = aci.payment_term_id
            left join account_payment_term_line aptl on aptl.payment_id = apt.id
            left join account_invoice aci_cn on aci_cn.id = aci.parent_invoice_id
        where
            aci.type in ('in_invoice', 'in_refund')
            %s
            and
            rc.select_to_interface_ofin = True
            and 
            (
            (aci.state = 'open' and rc.parent_company_id is null) 
            )
            and (aci.is_get_data_already = False or aci.is_get_data_already is null)
        order by 
            aci.date_invoice,aci.id
        ''' % (invoice_id_query,)
        self.env.cr.execute(query_str)
        data_invoice_ap = self.env.cr.dictfetchall()

        now_query_str = '-'.join(
            [
                str(now_utc.year),
                str(now_utc.month),
                str(now_utc.day)
            ]
        )

        head_log_values = line_log_values = {}

        group_res_id_branch, res_id_log_amount = self.prepare_data_for_compare_amount_of_data(
            'account.invoice',
            now_query_str
        )

        for invoice_ap in data_invoice_ap:
            invoice_obj_id = self.browse(invoice_ap['invoice_id'])

            # PREPARE FILE NAME
            str_now_with_branch = ''.join([
                invoice_ap['file_date'],
                invoice_ap['branch_code'][2:]
            ])

            if group_res_id_branch.get(invoice_ap['branch_code'], False):
                if invoice_ap['invoice_id'] in group_res_id_branch[invoice_ap['branch_code']]:
                    log_amount = res_id_log_amount[invoice_ap['invoice_id']]
                    log_amount += 1
                    log_amount_str = '{:02d}'.format(log_amount)
                else:
                    log_amount_str = '{:02d}'.format(1)
            else:
                log_amount_str = '{:02d}'.format(1)

            if invoice_obj_id.company_id.parent_company_id:
                branch_type = 'G'
            else:
                branch_type = 'S'

            ap_head_log_file = ap_head_dat_file = ''.join([
                'H',
                str_now_with_branch,
                branch_type,
                log_amount_str
            ])
            ap_line_log_file = ap_line_dat_file = ''.join([
                'L',
                str_now_with_branch,
                branch_type,
                log_amount_str
            ])

            ap_head_log_file += '.LOG'
            ap_head_dat_file += '.DAT'
            ap_line_log_file += '.LOG'
            ap_line_dat_file += '.DAT'

            # PREPARE DATA INVOICE HEAD
            if invoice_ap['vendor_code'] == 'F00000':
                if not invoice_obj_id.partner_id.partner_code:
                    vendor_code = invoice_obj_id.partner_id.get_partner_code()
                else:
                    vendor_code = invoice_obj_id.partner_id.partner_code
            else:
                vendor_code = invoice_ap['vendor_code']

            detail_in_head_dat_list = [
                self.put_blank_string(invoice_ap['source']),
                self.put_blank_string(invoice_ap['invoice_number']).ljust(50),
                self.put_blank_string(vendor_code.ljust(30)),
                self.put_blank_string(invoice_ap['vendor_invoice_date']),
                '{:014.2f}'.format(self.put_blank_string(invoice_ap['amount_total'])),
                self.put_blank_string(invoice_ap['branch_code']),
                self.put_blank_string(str(invoice_ap['invoice_type'])),
                self.put_blank_string(invoice_ap['import_good']),
                self.put_blank_string(invoice_ap['hold_reason']),
                self.put_blank_string(invoice_ap['invoice_tax_name']),
                self.put_blank_string(invoice_ap['tax_inv_no']).ljust(50),
                self.put_blank_string(invoice_ap['tempolary_field']),
                self.put_blank_string(invoice_ap['rtv_auth_no']),
                self.put_blank_string(invoice_ap['currency_code']),
                self.put_blank_string(invoice_ap['term_payment']),
                self.put_blank_string(invoice_ap['tempolary_field_2']),
                self.put_blank_string(invoice_ap['gr_tran_no']).ljust(15),
                self.put_blank_string(str(invoice_ap['ass_tax_invoice_num'])).ljust(50),
                self.put_blank_string(invoice_ap['tempolary_field_3']),
                self.put_blank_string(invoice_ap['tax_invoice_date']),
                self.put_blank_string(invoice_ap['invoice_rtv_type']),
                self.put_blank_string(invoice_ap['currency_rate']),
                self.put_blank_string(invoice_ap['due_date']),
                '\n'
            ]

            detail_in_head_dat = ''.join(detail_in_head_dat_list)

            # PREPARE DATA INVOICE LINE
            detail_in_line_dat_list = [
                self.put_blank_string(invoice_ap['source']),
                self.put_blank_string(invoice_ap['invoice_number']).ljust(50),
                self.put_blank_string(str(invoice_ap['invoice_type'])),
                self.put_blank_string(vendor_code.ljust(30)),
                'I',
                ' '.ljust(240),
                '{:014.2f}'.format(self.put_blank_string(invoice_ap['amount_total'])),
                str(1).ljust(14),
                ' '.ljust(14),
                ' '.ljust(35),
                ' '.ljust(5),
                ' '.ljust(8),
                self.put_blank_string(invoice_ap['origin_invoice'][:6]),
                '\n'
            ]

            detail_in_line_dat = ''.join(detail_in_line_dat_list)

            # UPDATE AMOUNT & DATA IN LOG FILE HEAD & LINE
            count_data_head_file = self.write_file_ofin(
                ap_head_dat_file,
                detail_in_head_dat,
                'dat'
            )
            count_data_line_file = self.write_file_ofin(
                ap_line_dat_file,
                detail_in_line_dat,
                'dat'
            )

            total_new_head = [0]
            total_old_head = [0]
            total_new_line = [0]
            total_old_line = [0]
            net_new_line = [0]

            if invoice_ap['amount_tax'] and invoice_obj_id.company_id.parent_company_id:
                amount_line = 2
            else:
                amount_line = 1

            if head_log_values.get(ap_head_log_file, False):

                total_new_head = head_log_values[ap_head_log_file]['total_new_line']
                total_new_line = line_log_values[ap_line_log_file]['total_new_line']
                net_new_line = head_log_values[ap_head_log_file]['net_amount']
                total_old_head = head_log_values[ap_head_log_file]['total_old_line']
                total_old_line = line_log_values[ap_line_log_file]['total_old_line']
                count_data_head_file = 0
                count_data_line_file = 0

            total_new_head.append(1)
            total_old_head.append(count_data_head_file)
            net_new_line.append(invoice_ap['amount_total'])
            total_new_line.append(amount_line)
            total_old_line.append(count_data_line_file)

            head_log_values[ap_head_log_file] = {
                'total_old_line': total_old_head,
                'total_new_line': total_new_head,
                'net_amount': net_new_line,
            }
            line_log_values[ap_line_log_file] = {
                'total_old_line': total_old_line,
                'total_new_line': total_new_line
            }

            head_log_value = head_log_values[ap_head_log_file]
            line_log_value = line_log_values[ap_line_log_file]

            amount_head_data = sum(head_log_value['total_old_line'] + head_log_value['total_new_line'])
            amount_line_data = sum(line_log_value['total_old_line'] + line_log_value['total_new_line'])
            net_amount = sum(head_log_value['net_amount'])

            detail_in_head_log = ''.join([
                ap_head_log_file,
                str(amount_head_data).ljust(10),
                '{:015.2f}'.format(net_amount)
            ])

            detail_in_line_log = ''.join([
                ap_line_log_file,
                str(amount_line_data).ljust(10),
                '{:015.2f}'.format(net_amount)
            ])

            self.write_file_ofin(ap_head_log_file, detail_in_head_log, 'log')
            self.write_file_ofin(ap_line_log_file, detail_in_line_log, 'log')

            # CASE INVOICE HAVE TAX AMOUNT
            if invoice_ap['amount_tax'] and invoice_obj_id.company_id.parent_company_id:
                detail_in_line_dat_list[4] = 'T'
                detail_in_line_dat_list[6] = '{:014.2f}'.format(
                    self.put_blank_string(invoice_ap['amount_tax'])
                )
                detail_in_line_dat_list[7] = ' '.ljust(14)

                detail_in_line_dat_vat = ''.join(detail_in_line_dat_list)
                self.write_file_ofin(ap_line_dat_file, detail_in_line_dat_vat, 'dat')

            # WRITE LOGWHEN DATA WRITE COMPELTE
            ofin_log_data_id = ofin_log_data_obj.create({
                'res_id': invoice_obj_id.id,
                'res_model': 'account.invoice',
                'log_amount': int(log_amount_str),
                'file_name_ref': ap_head_dat_file,
                'date_log_transaction': now_utc.date(),
                'branch_code': invoice_obj_id.branch_id.branch_code
            })

            # UPDATE INVOICE IS GET DATA ALREADY
            invoice_obj_id.update({
                'is_get_data_already': True
            })

            ofin_log_data_id.env.cr.commit()

            invoice_obj_id.env.cr.commit()
