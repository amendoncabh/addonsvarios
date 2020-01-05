# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    printed_price = fields.Float(
        string="Printed Price",
        required=True,
        default=0,
    )

    printed_date = fields.Datetime(
        string="Printed Date",
        required=False,
    )

    pricelists_start_date = fields.Datetime(
        string="Price-lists Start Date",
        required=False,
    )

    pricelists_end_date = fields.Datetime(
        string="Price-lists End Date",
        required=False,
    )
