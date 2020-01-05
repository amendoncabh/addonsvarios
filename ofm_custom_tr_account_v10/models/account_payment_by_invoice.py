# -*- coding: utf-8 -*-

from odoo import models, api, _, fields
from odoo.exceptions import UserError, ValidationError


class AccountPaymentLine(models.Model):
    _inherit = 'account.invoice.payment.line'

    paid_amount = fields.Float(
        strint='Paid Amount',
    )

    paid_amount_show = fields.Float(
        related='paid_amount',
        string="Paid amount",
        required=False,
        readonly=True,
    )

    is_check_full = fields.Boolean(
        string='Full',
        default=False,
    )

    @api.onchange('is_check_full')
    def onchange_check_full(self):
        self.paid_amount = 0
        if self.is_check_full:
            self.paid_amount = self.balance

    # def prepare_invoice_to_invoice_payment_line(self, invoice, vals):
    #     if invoice:
    #         balance = invoice.residual - invoice.credit_amt
    #
    #         if 'refund' in invoice.type:
    #             balance *= -1
    #
    #         vals.update({
    #             'dute_date': invoice.date_due,
    #             'amount': invoice.amount_total,
    #             'balance': balance,
    #             'wht_total': invoice.amount_wht,
    #             'currency_id': invoice.currency_id.id,
    #         })
    #
    #         return vals
    #
    # @api.model
    # def create(self, vals):
    #     if 'invoice_id' in vals and vals.get('invoice_id'):
    #
    #         invoice = self.env['account.invoice'].browse(vals.get('invoice_id'))
    #         vals = self.prepare_invoice_to_invoice_payment_line(invoice, vals)
    #
    #     return super(AccountPaymentLine, self).create(vals)
    #
    # @api.multi
    # def write(self, vals):
    #     if 'invoice_id' in vals and vals.get('invoice_id'):
    #
    #         invoice = self.env['account.invoice'].browse(vals.get('invoice_id'))
    #         vals = self.prepare_invoice_to_invoice_payment_line(invoice, vals)
    #
    #     return super(AccountPaymentLine, self).write(vals)

    # @api.multi
    # def check_full(self):
    #     for rec in self:
    #         super(AccountPaymentLine, rec).check_full()
    #         rec.payment_id._compute_invoice()
    #
    #         return True

