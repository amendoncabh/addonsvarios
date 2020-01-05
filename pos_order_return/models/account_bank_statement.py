# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    line_amount_returned = fields.Float(
        'Line Amount Returned',
        default=0.0,
        readonly=True,
    )

    original_line_id = fields.Many2one(
        'account.bank.statement.line',
        'Original Statement Line',
        readonly=True,
    )