# -*- coding: utf-8 -*-

from odoo import models, api


class CashBoxIn(models.TransientModel):

    _inherit = 'cash.box.in'

    @api.one
    def _calculate_values_for_statement_line(self, record):
        res = super(CashBoxIn, self)._calculate_values_for_statement_line(record)
        res['cash_box_type'] = 'in'
        return res


class CashBoxOut(models.TransientModel):

    _inherit = 'cash.box.out'

    @api.one
    def _calculate_values_for_statement_line(self, record):
        res = super(CashBoxOut, self)._calculate_values_for_statement_line(record)
        res['cash_box_type'] = 'out'
        return res
