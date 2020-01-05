from odoo import models, fields


class AccountTax(models.Model):
    _inherit = 'account.tax'

    suspend_tax = fields.Boolean(
        string='Suspend TAX',
        default=False
    )
    account_suspend_id = fields.Many2one(
        comodel_name='account.account',
        string='Account Suspend Tax',
        required=False
    )