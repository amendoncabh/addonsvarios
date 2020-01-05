# -*- coding: utf-8 -*-

import re

from odoo import models, fields, api, exceptions, _
from odoo.exceptions import ValidationError


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

    company_code_account_fc = fields.Char(
        string="Company Code FC",
        size=7,
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
        branch = self.env['pos.branch'].search(
            [
                ('pos_company_id', '=', self.id)
            ],
            limit=1
        )

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
                'partner_id': self.partner_id.id,
                'warehouse_id': self.env['stock.warehouse'].search([('company_id', '=', self.id)]).id,
                'flag_create_company': True,
            }

        # company_code_account = ""

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
            branch_id = self.env['pos.branch'].sudo(self.env.user.id).create(branch_values)
        else:
            branch_id = branch
            branch.sudo(self.env.user.id).write(branch_values)

        return branch_id

    @api.model
    def create(self, vals):
        self.check_company_code(vals)

        new_company = super(Company, self).create(vals)

        return new_company

    @api.multi
    def write(self, values):
        self.with_context(is_create_company=True).create_branch_auto(values)
        res = super(Company, self).write(values)
        return res
