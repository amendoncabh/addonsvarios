# -*- coding: utf-8 -*-

from odoo import fields, models


class PosPromotionProrate(models.Model):
    _name = 'pos.promotion.prorate'

    line_id = fields.Many2one(
        comodel_name="pos.order.line",
        string="Pos Order line",
        required=False,
        readonly=True,
    )

    sale_line_id = fields.Many2one(
        comodel_name="sale.order.line",
        string="Sale Order line",
        required=False,
        readonly=True,
    )

    promotion_id = fields.Many2one(
        comodel_name="pos.promotion",
        string="Promotion",
        required=False,
        readonly=True,
    )

    promotion_name = fields.Char(
        string="Promotion Name",
        related='promotion_id.promotion_name',
        required=False,
        readonly=True,
    )

    promotion_condition_id = fields.Many2one(
        comodel_name="pos.promotion.condition",
        string="Promotion Condition",
        required=False,
        readonly=True,
    )

    prorate_amount = fields.Float(
        string='Prorate Amount',
        default=0,
        readonly=True,
    )

    prorate_amount_exclude = fields.Float(
        string='Prorate Amount Exclude Vat',
        default=0,
        readonly=True,
    )

    prorate_vat = fields.Float(
        string='Prorate Vat',
        default=0,
        readonly=True,
    )

    is_manual_discount = fields.Boolean(
        string="Manual Discount",
        default=False,
    )

