# -*- coding: utf-8 -*-

from odoo import models, api
from odoo.exceptions import ValidationError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.multi
    def post(self):
        super(AccountPayment, self).post()
        for record in self:
            record.name = record.move_name

        for account_payment_line in self.invoice_line:
            account_payment_line.invoice_id.so_id.write({'state':  'done'})
