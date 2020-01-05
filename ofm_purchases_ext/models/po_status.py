# -*- coding: utf-8 -*-

from odoo import fields, models


class POStatus(models.Model):
    _name = 'po.status'
    _description = "PO Status"

    value = fields.Char(
        string="Value",
        required=False,
    )

    name = fields.Char(
        string="Name",
        required=False,
    )
