# -*- coding: utf-8 -*-

from odoo import api, fields, models



class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    approve_code = fields.Char(
        string='Approve Code',
        digit=6,
        readonly=True,
    )

    credit_card_type = fields.Selection(
        string="Type of Credit Card",
        selection=[
           ('VISA', 'VISA'),
           ('MAST', 'MAST'),
           ('TPNC', 'TPNC'),
           ('JCB', 'JCB'),
           ('KBANK', 'KBANK'),
           ('CUPC', 'CUPC'),
           ('QKBN', 'QKBN'),
        ],
        readonly=True,
    )

    credit_card_no = fields.Char(
        string='Credit Card No.',
        digit=16,
        readonly=True,
    )

    credit_card_no_encrypt = fields.Char(
        string='Credit Card No.',
        digit=16,
        compute='_credit_card_encrypt',
    )

    @api.multi
    @api.depends('credit_card_no')
    def _credit_card_encrypt(self):
        for record in self:
            if record.credit_card_no:
                credit_card_font = record.credit_card_no[:6]
                credit_card_back = record.credit_card_no[-4:]
                credit_card_replace = 'x' * (len(record.credit_card_no) - 10)

                record.credit_card_no_encrypt = credit_card_font + credit_card_replace + credit_card_back