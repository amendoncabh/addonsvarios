# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class BankTransferStatus(models.Model):
    _name = "bank.transfer.status"
    _rec_name = "name_th"

    code = fields.Char(
        string="Code",
        required=False,
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

    name_th = fields.Char(
        string="Status TH",
        required=False,
    )

    name_eng = fields.Char(
        string="Status ENG",
        required=False,
    )
