# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ReturnReason(models.Model):
    _name = "return.reason"

    name = fields.Char(
        string='Reason',
        required=True,
    )

    model = fields.Char(
        string='Model',
        required=True,
    )
