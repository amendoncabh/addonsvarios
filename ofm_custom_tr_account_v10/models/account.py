# -*- coding: utf-8 -*-
##############################################################################
#
#    ODOO, Open Source Management Solution
#    Copyright (C) 2016 Steigend IT Solutions
#    For more details, check COPYRIGHT and LICENSE files
#
##############################################################################
from odoo import api, models


class AccountAccount(models.Model):
    _inherit = 'account.account'

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=160):
        context = self._context or {}
        company_id = context.get('company_id', False)
        if company_id:
            if name:
                account_account_ids = self.search(
                    [
                        ('company_id', '=', company_id),
                        '|',
                        ('name', 'ilike', name),
                        ('code', 'ilike', name),
                    ] + args,
                    limit=limit
                )
            else:
                account_account_ids = self.search(
                    [
                        ('company_id', '=', company_id),
                    ] + args,
                    limit=limit
                )
            return account_account_ids.sudo().name_get()

        return super(AccountAccount, self).name_search(name, args, operator, limit)
