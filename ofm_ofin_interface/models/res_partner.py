# -*- coding: tis-620 -*-

import datetime
import pytz

from odoo import models, fields, api

list_fields = [
    'partner_code',
    'name',
    'vat',
    'property_payment_term_id',
    'property_supplier_payment_term_id',
    'street',
    'alley',
    'street2',
    'moo',
    'province_id',
    'amphur_id',
    'tambon_id',
    'zip',
    'phone',
    'mobile',
    'fax',
    'owner_first_name',
    'owner_last_name',
    'bank_account_count',
    'email',
    'branch_id',
]


class Company(models.Model):
    _inherit = "res.company"

    select_to_interface_ofin = fields.Boolean(
        'Select to Interface',
        copy=False,
        default=False,
    )

    parent_company_id = fields.Many2one(
        'res.company',
        string='Parent',
        track_visibility='always',
        store=True,
    )


class Partner(models.Model):
    _inherit = "res.partner"

    partner_code = fields.Char(
        string="Partner Code",
        reaonly=True,
    )

    oracle_branch_code = fields.Char(
        string="Oracle Branch Code",
        size=6,
    )

    is_edit_to_ofin = fields.Boolean(
        string="Is Edit To Ofin",
        default=False
    )

    bank_account_ids = fields.One2many(
        'res.partner.bank',
        'partner_id',
        string="All Bank Account"
    )

    date_archived = fields.Date(
        string="Date Archived"
    )

    @api.multi
    def write(self, vals):
        for record in self:
            for field in list_fields:
                if field in vals:
                    vals.update({
                        'is_edit_to_ofin': True
                    })
                    break

            if 'active' in vals:
                if vals.get('active'):
                    vals.update({
                        'date_archived': False
                    })
                else:
                    tr_convert = record.env['tr.convert']

                    now_utc = tr_convert.convert_datetime_to_bangkok(
                        datetime.datetime.now(pytz.timezone('UTC'))
                    )
                    vals.update({
                        'date_archived': now_utc
                    })

            res = super(Partner, record).write(vals)
            return res

    @api.multi
    def get_partner_code(self):
        for record in self:
            ir_sequence = record.env['ir.sequence']
            sequence_name = 'res.partner.sequence'
            ir_sequence_id = ir_sequence.search(
                [
                    ('name', '=', sequence_name)
                ]
            )
            if not ir_sequence_id:
                ir_sequence_id = ir_sequence.create({
                    'name': sequence_name,
                    'code': sequence_name,
                    'padding': 5,
                })
            if not record.partner_code:
                next_sequence = ir_sequence_id.next_by_id()
                partner_code = ''.join([
                    'F',
                    next_sequence
                ])
                record.update({
                    'partner_code': partner_code
                })

            return record.partner_code

    def ofin_interface_text_vendor(self):

        tr_convert = self.env['tr.convert']

        ofin_log_data_obj = self.env['ofin.log.data.to.file']

        account_invoice = self.env['account.invoice']

        now_utc = tr_convert.convert_datetime_to_bangkok(
            datetime.datetime.now(pytz.timezone('UTC'))
        )
        now_to_str = ''.join([
            '{:02d}'.format(now_utc.year % 100),
            '{:02d}'.format(now_utc.month),
            '{:02d}'.format(now_utc.day)
        ])
        now_time_to_str = ''.join([
            '{:02d}'.format(now_utc.hour),
            '{:02d}'.format(now_utc.minute),
            '{:02d}'.format(now_utc.second)
        ])

        query_str = """
        select 
            id,is_edit_to_ofin,active
        from 
            res_partner rp
        where 
            partner_code is not null
        """
        self.env.cr.execute(query_str)
        partners_result = self.env.cr.dictfetchall()

        date_log_transaction = now_utc.date().isoformat()

        query_str = """
        select 
            res_id,max(log_amount) as log_amount
        from 
            ofin_log_data_to_file ofin_log
        where
            res_model = 'res.partner'
            and
            date_log_transaction = '%s' 
        group by
            res_id
        """ % date_log_transaction
        self.env.cr.execute(query_str)
        logs_result = self.env.cr.dictfetchall()
        log_res_ids = []
        map_res_log_amount = {}
        partner_ids = []

        for item in logs_result:
            key = item['res_id']
            if not map_res_log_amount.get(key, False):
                map_res_log_amount.update({
                    key: item['log_amount']
                })
            log_res_ids.append(key)

        map_partner_status = {}
        for item in partners_result:
            status_char = ''
            if item['id'] in log_res_ids:
                if item['active'] is False:
                    status_char = 'D'
                elif item['is_edit_to_ofin'] is True:
                    status_char = 'M'
            else:
                status_char = 'A'

            if len(status_char) != 0:
                map_partner_status.update({
                    item['id']: status_char
                })
                partner_ids.append(item['id'])

        if partner_ids:

            head_log_values = {}

            for partner_id in self.browse(partner_ids):
                key = partner_id.id
                log_amount = map_res_log_amount.get(key, False)
                if log_amount:
                    log_amount += 1
                    log_amount_str = '{:1d}'.format(log_amount)
                else:
                    log_amount_str = '{:1d}'.format(1)

                file_name = ''.join([
                    'S',
                    now_to_str,
                    log_amount_str
                ])

                text_file_vat_name = '.'.join([
                    file_name,
                    'VAL'
                ])
                text_file_dat_name = '.'.join([
                    file_name,
                    'DAT'
                ])

                if map_partner_status[key] == 'D':
                    delete_date = partner_id.date_archived
                else:
                    delete_date = ' '.ljust(6)

                term_payment_id = self.env['ir.property'].search(
                    [
                        ('res_id', '=', partner_id.id),
                        ('name', '=', 'property_payment_term_id'),
                    ],
                    limit=1
                )

                bank_account_id = partner_id.bank_account_ids[0] if partner_id.bank_account_ids else False
                if bank_account_id:
                    bic = bank_account_id.bank_id.bic if bank_account_id.bank_id.bic else ' '
                    acc_number = bank_account_id.acc_number if bank_account_id.acc_number else ' '
                else:
                    bic = ''
                    acc_number = ''

                phone = partner_id.phone if partner_id.phone else partner_id.mobile
                phone = phone if phone else ' '

                owner_first_name = partner_id.owner_first_name if partner_id.owner_first_name else ' '
                owner_last_name = partner_id.owner_last_name if partner_id.owner_last_name else ' '
                email = partner_id.email if partner_id.email else ' '
                branch_id = partner_id.branch_id if partner_id.branch_id else '0'


                if term_payment_id:
                    term_payment_days = term_payment_id.line_ids.days
                else:
                    term_payment_days = 0

                alley = ''.join([
                    u'ยซร?ร?.',
                    partner_id.alley,
                    ' '
                ]) if partner_id.alley else ' '

                road = ''.join([
                    u'ยถ.',
                    partner_id.street2,
                    ' '
                ]) if partner_id.street2 else ' '

                moo = ''.join([
                    u'ร?ร?ร?รจ.',
                    partner_id.moo,
                    ' '
                ]) if partner_id.moo else ' '

                tambon = ''.join([
                    u'๏ฟฝ.',
                    partner_id.tambon_id.name,
                    ' '
                ]) if partner_id.tambon_id else ' '

                amphur = ''.join([
                    u'๏ฟฝ.',
                    partner_id.amphur_id.name,
                    ' '
                ]) if partner_id.amphur_id else ' '

                province_code = ''.join([
                    'BKK' if partner_id.province_id.code == '10' else ' '
                ]) if partner_id.province_id else ' '

                list_dat_file_detail = [
                    map_partner_status[key],
                    delete_date,
                    partner_id.partner_code,
                    partner_id.name.ljust(60),
                    ' ',
                    partner_id.vat.ljust(13),
                    '{:04d}'.format(term_payment_days),
                    '2',
                    '07.00',
                    '0',
                    (partner_id.street + moo).ljust(60),
                    (alley + road).ljust(60),
                    (tambon + amphur).ljust(60),
                    (partner_id.province_id.name if partner_id.province_id else ' ').ljust(25),
                    (province_code).ljust(4),
                    (partner_id.zip_id.name if partner_id.zip_id else ' ').ljust(10),
                    'THA',
                    ('Thailand').ljust(25),
                    (phone).ljust(15),
                    ' '.ljust(15),
                    ' '.ljust(15),
                    (owner_first_name).ljust(15),
                    (owner_last_name).ljust(20),
                    'N',
                    bic.ljust(3),
                    acc_number.replace("-", "").ljust(30),
                    partner_id.name.ljust(65),
                    email.ljust(50),
                    ' '.ljust(20),
                    '  ',
                    'THB',
                    branch_id.ljust(10),
                    ' '.ljust(30),
                    '\n'
                ]

                detail_vendor_dat_file = ''.join(list_dat_file_detail)

                count_data_head_file = account_invoice.write_file_ofin(
                    text_file_dat_name,
                    detail_vendor_dat_file,
                    'dat'
                )

                total_new_dat = []
                total_old_dat = []

                if head_log_values.get(text_file_vat_name, False):
                    total_new_dat = head_log_values[text_file_vat_name]['total_new_dat']
                    count_data_head_file = 0

                total_new_dat.append(1)
                total_old_dat.append(count_data_head_file)

                head_log_values[text_file_vat_name] = {
                    'total_old_dat': total_old_dat,
                    'total_new_dat': total_new_dat,
                }

                head_log_value = head_log_values[text_file_vat_name]

                amount_head_data = sum(
                    head_log_value['total_old_dat'] + head_log_value['total_new_dat']
                )

                list_vat_file_detail = [
                    'HDR',
                    text_file_vat_name,
                    '{:09d}'.format(2),
                    now_to_str,
                    now_time_to_str,
                    '0'.ljust(15),
                    '0'.ljust(15),
                    '0'.ljust(15),
                    '0'.ljust(15),
                    '\n'
                ]

                detail_head_to_str = ''.join(list_vat_file_detail)

                list_vat_file_detail[0] = 'TRL'
                list_vat_file_detail[1] = text_file_dat_name
                list_vat_file_detail[2] = '{:09d}'.format(amount_head_data)

                detail_head_to_str += ''.join(list_vat_file_detail)

                account_invoice.write_file_ofin(text_file_vat_name, detail_head_to_str, 'log')

                ofin_log_data_id = ofin_log_data_obj.create({
                    'res_id': key,
                    'res_model': 'res.partner',
                    'log_amount': int(log_amount_str),
                    'file_name_ref': text_file_dat_name,
                    'date_log_transaction': now_utc.date(),
                })

                partner_id.is_edit_to_ofin = False

                partner_id.env.cr.commit()

                ofin_log_data_id.env.cr.commit()

    @api.onchange('property_supplier_payment_term_id')
    def onchange_property_supplier_payment_term_id(self):
        if self.property_supplier_payment_term_id:
            self.update({
                'property_payment_term_id': self.property_supplier_payment_term_id.id
            })
        else:
            self.update({
                'property_payment_term_id': False
            })

    @api.onchange('property_payment_term_id')
    def onchange_property_payment_term_id(self):
        if self.property_payment_term_id:
            self.update({
                'property_supplier_payment_term_id': self.property_payment_term_id.id
            })
        else:
            self.update({
                'property_supplier_payment_term_id': False
            })


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    @api.model
    def create(self, vals):
        if vals.get('partner_id', False):
            partner_id = self.env['res.partner'].browse(vals['partner_id'])
            partner_id.write({
                'is_edit_to_ofin': True
            })
        res = super(ResPartnerBank, self).create(vals)
        return res

    @api.multi
    def write(self, vals):
        if vals.get('partner_id', False):
            partner_id = self.env['res.partner'].browse(vals['partner_id'])
            partner_id.write({
                'is_edit_to_ofin': True
            })
        else:
            partner_id = self.env['res.partner'].browse(self.partner_id.id)
            partner_id.write({
                'is_edit_to_ofin': True
            })
        res = super(ResPartnerBank, self).write(vals)
        return res
