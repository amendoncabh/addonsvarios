# -*- coding: utf-8 -*-

import re

from odoo import models, fields, api, exceptions, _
from odoo.exceptions import ValidationError


class ResPartnerOFM(models.Model):
    _inherit = 'res.partner'

    company_code_account = fields.Char(
        string="Company Code",
        size=4,
    )

    @api.multi
    def _display_address(self, without_company=False):
        res = super(ResPartnerOFM, self)._display_address(without_company)

        address_format = "%(street)s %(alley)s"
        address_format += "%(street2)s "
        address_format += "%(moo)s\n" if self.moo else ''
        address_format += "แขวง/ตำบล %(tambon)s " if self.tambon_id.name else ''
        address_format += "เขต/อำเภอ %(amphur)s\n" if self.amphur_id.name else ''
        address_format += " %(province)s" if self.province_id.id == self.env.ref('base.province_2').id \
            else " จังหวัด %(province)s" if self.province_id else ''
        address_format += " %(zip)s\n"
        address_format += "โทร. %(phone)s\n" if self.phone else ''
        address_format += "เลขประจำตัวผู้เสียภาษี: %(vat)s" if self.vat else ''

        args = {
            'street': self.street or '',
            'alley': self.alley or '',
            'street2': self.street2 or '',
            'moo': self.moo or '',
            'tambon': self.tambon_id.name or '',
            'amphur': self.amphur_id.name or '',
            'province': self.province_id.name or '',
            'zip': self.zip_id.name or '',
            'vat': self.vat or '',
            'company_name': self.commercial_company_name or '',
            'phone': self.phone or '',
        }

        if without_company:
            args['company_name'] = ''
        elif self.commercial_company_name:
            address_format = '%(company_name)s\n' + address_format

        return address_format % args

    def get_new_addr(self):
        addr = self
        s = ""
        if addr.street:
            s += u" " + addr.street
        if addr.moo:
            s += u" " + addr.moo
        if addr.alley:
            s += u" " + addr.alley
        if addr.street2:
            s += u" " + addr.street2
        if addr.tambon_id:
            if addr.province_id.name_eng == 'Bangkok':
                s += u" แขวง" + addr.tambon_id.name
            else:
                s += u" ตำบล" + addr.tambon_id.name
        if addr.amphur_id:
            if addr.province_id.name_eng == 'Bangkok':
                s += u" เขต" + addr.amphur_id.name
            else:
                s += u" อำเภอ" + addr.amphur_id.name
        if addr.province_id:
            if addr.province_id.name_eng == 'Bangkok':
                s += u" " + addr.province_id.name
            else:
                s += u" จังหวัด" + addr.province_id.name
        if addr.zip:
            s += " " + addr.zip
        return s

    @api.multi
    def _sale_total_deposit(self):
        sale_order = self.env['sale.order']
        all_partners_and_children = {}
        all_partner_ids = []

        for partner in self:
            all_partners_and_children[partner] = self.search([('id', 'child_of', partner.id)]).ids
            all_partner_ids += all_partners_and_children[partner]

            # for partner in self:
            sale = sale_order.search([
                ('partner_id', 'in', all_partner_ids),
                ('state', '=', 'sale'),
                ('deposit_ids.state', 'in', ['open', 'paid']),
            ])
            total_deposit = 0
            for sl in sale:
                total_deposit += sl.amount_total

            partner.aging_balance += total_deposit
            if partner.aging_balance > partner.max_aging:
                partner.aging_balance = partner.max_aging

    def get_res_partner_by_query(self):
        partner_id = self._context.get('partner_id', 0)

        query_key = {
            'partner_id': "parent_id = {0} or id = {1}".format(partner_id, partner_id) if partner_id else "",
            'is_customer': 'customer is true and parent_id is null',
            'is_invoice': "type = 'invoice'",
            'is_shipping': "type = 'delivery'",
            'is_contact': "type = 'contact'",
            'is_billing': "type = 'billing'",
        }

        ctx = dict(self._context)
        query_where = ""

        for item_key, item_value in query_key.iteritems():
            if item_key in ctx:
                if ctx.get(item_key, False):
                    if query_where != "":
                        query_where = ''.join([
                            query_where,
                            'and ',
                            item_value
                        ])
                    else:
                        query_where = ''.join([
                            query_where,
                            item_value
                        ])

        if query_where != "":
            query_where = ''.join([
                'where ',
                query_where
            ])

        query_str = """
            select id
            from res_partner
            {0}
        """.format(query_where)

        self.env.cr.execute(query_str)
        result_model = self.env.cr.dictfetchall()

        res_partner_ids = []

        for result_data in result_model:
            res_partner_id = result_data.get('id', False)

            if res_partner_id:
                res_partner_ids.append(result_data.get('id'))

        return res_partner_ids

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        is_query = self._context.get('is_query', False)

        if is_query:
            res_partner_ids = self.get_res_partner_by_query()

            if len(res_partner_ids) > 0:
                args += [('id', 'in', res_partner_ids)]

        return super(ResPartnerOFM, self).search(args, offset, limit, order, count)

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=160):
        is_query = self._context.get('is_query', False)
        limit = 8

        if is_query:
            res_partner_id = self.env['res.partner'].search([])

            return res_partner_id.sudo().name_get()

        return super(ResPartnerOFM, self).name_search(name, args, operator, limit)


class Company(models.Model):
    _inherit = "res.company"

    def _default_nationality_id(self):
        return self.env.ref('base.th')

    company_code_account = fields.Char(
        string="Company Code",
        related='partner_id.company_code_account',
        size=4,
        required=True,
    )

    ofin_code_first_branch = fields.Char(
        string="Ofin Short Code First Branch",
        size=2,
        required=True,
    )

    bustype = fields.Integer(
        string="BusType",
        required=True,
        help="Business Type",
        default=1,
    )

    group = fields.Char(
        string="Group",
        required=True,
        help="Shop Group",
        default="05"
    )

    alley = fields.Char(
        string='Alley',
    )

    moo = fields.Char(
        string='Moo',
    )

    tambon_id = fields.Many2one(
        'tambon',
        string='Tambon/Khwaeng',
        track_visibility='always',
        required=True,
    )

    amphur_id = fields.Many2one(
        'amphur',
        string='Amphur/Khet',
        track_visibility='always',
        required=True,
    )

    province_id = fields.Many2one(
        'province',
        string='Province',
        track_visibility='always',
        required=True,
    )

    zip_id = fields.Many2one(
        'zip',
        string='Zip',
        track_visibility='always',
        required=True,
    )

    zip = fields.Char(
        required=False,
    )

    nationality_id = fields.Many2one(
        'res.country',
        string='Nationality',
        default=_default_nationality_id,
        required=True,
    )

    country_id = fields.Many2one(
        required=False,
    )

    state_id = fields.Many2one(
        required=False,
    )

    city = fields.Char(
        required=False,
    )

    @api.multi
    @api.constrains('group')
    def _check_allow_only_number(self):
        pattern = "^[0-9]*$"

        for record in self:
            if record.branch_ids.branch_id:
                if re.match(pattern, str(record.branch_ids.branch_id)):
                    is_number = True
                else:
                    is_number = False

                if is_number is False:
                    raise exceptions.ValidationError(
                        _("Branch ID must number only."))

    @api.model
    def check_company_code(self, vals):
        if len(vals['company_code_account']) < 4:
            raise ValidationError(_('Company Code must 4 digit.'))
        else:
            return True

    @api.model
    def create_branch_auto(self, values):
        # Create Branch
        branch = self.env['pos.branch'].search([
            ('pos_company_id', '=', self.id)
        ])

        branch_values = {}

        if not branch:
            branch_values = {
                'branch_name': self.name,
                'street': self.street,
                'alley': self.alley,
                'street2': self.street2,
                'moo': self.moo,
                'province_id': self.province_id.id,
                'amphur_id': self.amphur_id.id,
                'tambon_id': self.tambon_id.id,
                'zip_id': self.zip_id.id,
                'zip': self.zip,
                'nationality_id': self.nationality_id.id,
                'pos_company_id': self.id,
                'branch_id': '00000',
                'warehouse_id': self.env['stock.warehouse'].search([('company_id', '=', self.id)]).id,
                'flag_create_company': True,
                'ofin_code': self.ofin_code_first_branch
            }

        company_code_account = ""

        if values.get('company_code_account', False):
            company_code_account = str(values.get('company_code_account'))
        else:
            company_code_account = self.company_code_account

        if values.get('company_code_account', False) \
                or not branch:
            branch_no = '00' if not branch.branch_code else branch.branch_code[-2:]
            branch_values.update({
                'branch_code': company_code_account + branch_no
            })

        if not branch:
            self.env['pos.branch'].sudo(self.env.user.id).create(branch_values)
        else:
            branch.sudo(self.env.user.id).write(branch_values)

        return True

    @api.model
    def create(self, vals):
        self.check_company_code(vals)

        new_company = super(Company, self).create(vals)

        return new_company

    @api.multi
    def write(self, values):
        self.create_branch_auto(values)

        return super(Company, self).write(values)


class PosBranch(models.Model):
    _inherit = 'pos.branch'

    def _default_nationality_id(self):
        return self.env.ref('base.th')

    alley = fields.Char(
        string='Alley',
    )

    moo = fields.Char(
        string='Moo',
    )

    tambon_id = fields.Many2one(
        'tambon',
        string='Tambon/Khwaeng',
        track_visibility='always',
        required=True,
    )

    amphur_id = fields.Many2one(
        'amphur',
        string='Amphur/Khet',
        track_visibility='always',
        required=True,
    )

    province_id = fields.Many2one(
        'province',
        string='Province',
        track_visibility='always',
        required=True,
    )

    zip_id = fields.Many2one(
        'zip',
        string='Zip',
        track_visibility='always',
        required=True,
    )

    zip = fields.Char(
        required=False,
    )

    nationality_id = fields.Many2one(
        'res.country',
        string='Nationality',
        default=_default_nationality_id,
        required=True,
    )

    country_id = fields.Many2one(
        required=False,
    )

    state_id = fields.Many2one(
        required=False,
    )

    city = fields.Char(
        required=False,
    )

    def get_res_partner_by_query(self):
        partner_id = self._context.get('partner_id', 0)

        query_key = {
            'partner_id': "parent_id = {0} or id = {1}".format(partner_id, partner_id) if partner_id else "",
            'is_customer': 'customer is true and parent_id is null',
            'is_invoice': "type = 'invoice'",
            'is_shipping': "type = 'delivery'",
            'is_contact': "type = 'contact'",
            'is_billing': "type = 'billing'",
        }

        ctx = dict(self._context)
        query_where = ""

        for item_key, item_value in query_key.iteritems():
            if item_key in ctx:
                if ctx.get(item_key, False):
                    if query_where != "":
                        query_where = ''.join([
                            query_where,
                            'and ',
                            item_value
                        ])
                    else:
                        query_where = ''.join([
                            query_where,
                            item_value
                        ])

        if query_where != "":
            query_where = ''.join([
                'where ',
                query_where
            ])

        query_str = """
            select id
            from res_partner
            {0}
        """.format(query_where)

        self.env.cr.execute(query_str)
        result_model = self.env.cr.dictfetchall()

        res_partner_ids = []

        for result_data in result_model:
            res_partner_id = result_data.get('id', False)

            if res_partner_id:
                res_partner_ids.append(result_data.get('id'))

        return res_partner_ids

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        is_query = self._context.get('is_query', False)

        if is_query:
            res_partner_ids = self.get_res_partner_by_query()

            if len(res_partner_ids) > 0:
                args += [('id', 'in', res_partner_ids)]

        return super(PosBranch, self).search(args, offset, limit, order, count)

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=160):
        is_query = self._context.get('is_query', False)
        limit = 8

        if is_query:
            res_partner_id = self.env['res.partner'].search([])

            return res_partner_id.sudo().name_get()

        return super(PosBranch, self).name_search(name, args, operator, limit)

