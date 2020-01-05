# -*- coding: utf-8 -*-

from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = "sale.order"

    daily_summary_franchise_id = fields.Many2one(
        comodel_name="daily.summary.franchise",
        string="Daily Summary Franchise",
        required=False,
        index=True,
    )
