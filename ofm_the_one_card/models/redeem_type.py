# -*- coding: utf-8 -*-

from odoo import api, fields, models
from openerp.exceptions import UserError


class RedeemType(models.Model):
    _name = 'redeem.type'
    
    name = fields.Char(
        string='Name',
        required=True
    )

    code = fields.Char(
        string='Short Code'
    )

    description = fields.Text(
        string='Description'
    )

    is_t1c = fields.Boolean(
        string='Is T1C',
        default=False
    )

    is_bank_transfer = fields.Boolean(
        string='Is Bank Transfer',
        default=False
    )

    active = fields.Boolean(
        string='Active',
        default=True
    )