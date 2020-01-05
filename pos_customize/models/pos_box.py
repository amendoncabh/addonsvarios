# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountBankStatementLine(models.Model):

    _inherit = "account.bank.statement.line"

    cash_box_type = fields.Char(string='Cash Box Type')
