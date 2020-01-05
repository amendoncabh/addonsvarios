# -*- coding: utf-8 -*-

from odoo import api
from odoo import models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def _payment_fields(self, ui_paymentline):
        res = super(PosOrder, self)._payment_fields(ui_paymentline)
        res.update({
            'approve_code': ui_paymentline['approve_code'],
            'credit_card_no': ui_paymentline['credit_card_no'],
            'credit_card_type': ui_paymentline['credit_card_type'],
        })
        return res

    @api.model
    def _prepare_bank_statement_line_payment_values(self, data):
        res = super(PosOrder, self)._prepare_bank_statement_line_payment_values(data)
        if 'credit_card_no' in data:
            res.update({
                'approve_code': data['approve_code'],
                'credit_card_no': data['credit_card_no'],
                'credit_card_type': data['credit_card_type'],
            })
        return res
