# -*- coding: utf-8 -*-

from odoo import fields, models


class SOPaymentType(models.Model):
    _name = "so.payment.type"

    customer_type = fields.Char(
        string="Customer Type",
        required=True,
    )

    name = fields.Char(
        string="Name",
        required=True,
    )

    type_sale_ofm = fields.Boolean(
        string='Type Sale OFM',
        readonly=True,
    )
