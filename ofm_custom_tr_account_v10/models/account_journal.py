from odoo import fields, models, api


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    flag_change = fields.Boolean(
        string='Can Change',
        default=True,
        help='This field is flag, setting for thia payment method can get change on POS'
    )

    default_credit_rounding_account_id = fields.Many2one(
        'account.account', string='Default Credit Rounding Account',
        domain=[('deprecated', '=', False)],
    )

    default_debit_rounding_account_id = fields.Many2one(
        'account.account', string='Default Debit Rounding Account',
        domain=[('deprecated', '=', False)],
    )

    default_credit_deposit_account_id = fields.Many2one(
        'account.account', string='Default Credit Deposit Account',
    )

    default_debit_deposit_account_id = fields.Many2one(
        'account.account', string='Default Debit Deposit Account',
    )

    @api.model
    def create(self, vals):
        journal = super(AccountJournal, self).create(vals)
        if vals.get('type') in ('bank', 'cash'):
            journal.journal_user = True
        return journal

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=160):
        context = self._context or {}
        company_id = context.get('company_id', False)
        print context
        if company_id:
            if name:
                account_journal_ids = self.search(
                    [
                        ('company_id', '=', company_id),
                        '|',
                        ('name', 'ilike', name),
                    ] + args,
                    limit=limit
                )
            else:
                account_journal_ids = self.search(
                    [
                        ('company_id', '=', company_id),
                    ] + args,
                    limit=limit
                )
            return account_journal_ids.sudo().name_get()

        return super(AccountJournal, self).name_search(name, args, operator, limit)