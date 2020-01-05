# -*- coding: utf-8 -*-

from odoo import fields, models


class TypeToOFM(models.Model):
    _name = 'type.to.ofm'
    _description = "TypeToOFM"

    value = fields.Char(
        string="Values",
        required=True,
    )

    name = fields.Char(
        string="Name",
        required=True,
    )
