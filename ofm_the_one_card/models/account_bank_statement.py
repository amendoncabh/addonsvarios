# -*- coding: utf-8 -*-

from odoo import models
from odoo import api, fields, models, _


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    t1cc_barcode = fields.Char(
        string='T1CC Barcode',
        readonly=True
    )

    t1cp_receipt_no = fields.Char(
        string='T1CP Receipt No.',
        readonly=True
    )

    transactions = fields.Char(
        string='Transactions',
        readonly=True
    )

    api_to_be_cancelled = fields.Boolean(
        string="API Cancel",
        readonly=True
    )

    api_cancel_success = fields.Boolean(
        string="API Cancel Success",
        readonly=True
    )

    @api.model
    def check_duplicate_t1cc(self, barcode):
        possible_duplicates = self.search([('t1cc_barcode', '=', str(barcode))])

        #counting for orders and void orders with the barcode
        void_orders = 0
        orders = 0

        for duplicate in possible_duplicates:
            pos_statement = duplicate.pos_statement_id

            if pos_statement.is_void_order:
                void_orders += 1
            else:
                orders += 1

        #if the number of void orders is greater than the number of orders, that means we can safely used the coupon,
        #else it must be a duplicate
        if void_orders >= orders:
            return 0
        else:
            return 1