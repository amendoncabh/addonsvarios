# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    return_reason_id = fields.Many2one(
        comodel_name="return.reason",
        string="Reason",
    )
