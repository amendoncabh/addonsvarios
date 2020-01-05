# -*- coding: utf-8 -*-

from odoo import fields, models


class ProductCategory(models.Model):
    _inherit = "product.category"

    property_stock_return_account = fields.Many2one(
        comodel_name="account.account",
        string="Stock Return Account",
        company_dependent=True,
        required=False,
        domain=[('deprecated', '=', False)],
        oldname="property_stock_return_account",
    )
    expense_refund_account = fields.Many2one(
        comodel_name="account.account",
        string="Expense Refund Account",
        company_dependent=True,
        required=False,
        domain=[('deprecated', '=', False)],
        oldname="expense_refund_account",
    )
