# -*- coding: utf-8 -*-

from odoo import api, fields, models


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    daily_summary_franchise_id = fields.Many2one(
        comodel_name="daily.summary.franchise",
        string="Daily Summary Franchise",
        required=False,
        index=True,
    )
