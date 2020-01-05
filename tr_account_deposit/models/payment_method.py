from odoo import models, fields, api


class AccountPaymentMethod(models.Model):
    _inherit = 'account.payment.method.multi'

    @api.model
    def payment_method_default_cash(self):
        payment_cash = self.env['ir.config_parameter'].search([
            ('key', '=', 'deposit_default_payment_cash')
        ]).value

        company_ids = self.env['res.company'].search([])

        if company_ids:
            for company_id in company_ids:
                journal_cash = self.env['account.journal'].search([
                    ('type', '=', payment_cash),
                    ('company_id', '=', company_id.id),
                ])

                if journal_cash:
                    payment_method_obj = self.env['account.payment.method.multi']

                    payment_method_id = payment_method_obj.search([
                        ('property_account_payment_method_id', '=', journal_cash.id),
                    ])

                    if not payment_method_id:
                        payment_method_obj.create({
                            'name': 'Cash',
                            'type': payment_cash,
                            'company_id': company_id.id,
                            'journal_id': journal_cash.id,
                            'property_account_payment_method_id': journal_cash.default_credit_account_id.id,
                            'percent': 100,
                        })

    @api.model
    def payment_method_default_credit_card(self):
        payment_credit_card = self.env['ir.config_parameter'].search([
            ('key', '=', 'deposit_default_payment_credit_card')
        ]).value

        company_ids = self.env['res.company'].search([])

        if company_ids:
            for company_id in company_ids:
                journal_credit_card = self.env['account.journal'].search([
                    ('type', '=', payment_credit_card),
                    ('company_id', '=', company_id.id),
                ])

                if journal_credit_card:
                    payment_method_obj = self.env['account.payment.method.multi']

                    payment_method_id = payment_method_obj.search([
                        ('property_account_payment_method_id', '=', journal_credit_card.id),
                    ])

                    if not payment_method_id:
                        payment_method_obj.create({
                            'name': 'Credit Card',
                            'type': payment_credit_card,
                            'company_id': company_id.id,
                            'journal_id': journal_credit_card.id,
                            'property_account_payment_method_id': journal_credit_card.default_credit_account_id.id,
                            'percent': 100,
                        })
