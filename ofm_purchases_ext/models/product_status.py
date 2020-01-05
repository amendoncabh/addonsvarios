# -*- coding: utf-8 -*-

from odoo import fields, models


class ProductStatus(models.Model):
    _name = 'product.status'
    _description = "Product Status"

    value = fields.Char(
        string="Values",
        required=True,
    )

    name = fields.Char(
        string="Name",
        required=True,
    )
