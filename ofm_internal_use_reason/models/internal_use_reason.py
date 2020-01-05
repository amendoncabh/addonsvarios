# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class InternalUseReason(models.Model):
    _name = "internal.use.reason"
    _description = "Internal use reason and accounting record"

    name = fields.Char(
        string = 'Name',
        required = True
    )
    company_id = fields.Many2one(
        'res.company',
        string = 'Company',
        required = True
    )
    credit_account_id = fields.Many2one(
        'account.account',
        string = 'Accounting',
        required = True
    )
    debit_account_id = fields.Many2one(
        'account.account',
        string = 'Accounting',
        required = True
    )

