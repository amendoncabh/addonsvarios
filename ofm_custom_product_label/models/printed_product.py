# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api
from odoo.exceptions import except_orm, UserError
from odoo.tools.translate import _

class PrintedProduct(models.Model):
    _name = "printed.product"

    branch_id = fields.Many2one(
        comodel_name="pos.branch",
        string="",
        required=True,
    )

    product_id = fields.Many2one(
        comodel_name="product.product",
        string="",
        required=True,
    )

    printed_price = fields.Float(
        string="Printed Price",
        required=True,
        default=0,
    )

    pricelists_start_date = fields.Datetime(
        string="Price-lists Start Date",
        required=False,
    )

    pricelists_end_date = fields.Datetime(
        string="Price-lists End Date",
        required=False,
    )