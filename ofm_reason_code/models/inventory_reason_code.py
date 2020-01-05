# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class InventoryReasonCode(models.Model):
    _name = "inventory.reason.code"
    _description = "Reason Code of Inventory"

    name = fields.Char(
        string = 'Name',
        required = True
    )