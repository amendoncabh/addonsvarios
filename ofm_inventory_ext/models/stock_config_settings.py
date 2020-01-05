# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockSettings(models.TransientModel):
    _inherit = 'stock.config.settings'

    max_previous_month = fields.Integer(
        string="Max Previous Month (Average Price)",
        required=True,
        default=1,
        description="Min value is 0 and max value is 12"
    )

    @api.onchange('max_previous_month')
    def _onchange_max_previous_month(self):
        if 0 > self.max_previous_month or self.max_previous_month > 12:
            self.max_previous_month = 0

