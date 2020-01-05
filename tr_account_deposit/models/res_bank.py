from odoo import models, fields


class Bank(models.Model):
    _inherit = "res.bank"

    account_bank_id = fields.Many2one(
        comodel_name='account.account',
        string='Account Bank',
        required=False
    )
    bank_thai = fields.Selection(
        selection=[
            ('scb', 'SCB'),
            ('bbl', 'BBL'),
            ('kbank', 'KBank'),
            ('ktb', 'KTB'),
            ('tmb', 'TMB'),
            ('bay', 'BAY')
        ],
        string='Bank',
        required=True,
        default='kbank'
    )