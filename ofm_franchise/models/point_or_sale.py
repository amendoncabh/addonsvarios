# -*- coding: utf-8 -*-

from odoo import models, fields


class PosOrder(models.Model):
    _inherit = 'pos.order'

    daily_summary_franchise_id = fields.Many2one(
        comodel_name="daily.summary.franchise",
        string="Daily Summary Franchise",
        required=False,
        index=True,
    )
