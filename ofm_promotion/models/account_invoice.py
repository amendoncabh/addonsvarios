# -*- coding: utf-8 -*-

import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)

class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    promotion_id = fields.Many2one(
        comodel_name='pos.promotion',
        string='Promotion ID',
        readonly=True,
        ondelete='restrict'
    )

    promotion_condition_id = fields.Many2one(
        comodel_name='pos.promotion.condition',
        string='Promotion Condition ID',
        readonly=True,
        ondelete='restrict'
    )

    promotion_type = fields.Selection(
        related='promotion_id.promotion_type',
        selection=[
            ('step', 'Step'),
            ('loop', 'Loop'),
            ('discount', 'Discount')
        ],
        string='Promotion Type',
        readonly=True,
    )

    promotion_name = fields.Char(
        string='Promotion',
        readonly=True,
    )

    promotion = fields.Boolean(
        'Is Promotion'
    )

    free_product_id = fields.Many2one(
        comodel_name='product.product',
        string="Reward Product",
        required=False,
        readonly=True,
    )

    prorate_amount = fields.Float(
        string='Prorate Amount',
        default=0,
        store=True,
        readonly=True,
    )

    prorate_amount_exclude = fields.Float(
        string='Prorate Amount Exclude Vat',
        default=0,
        store=True,
        readonly=True,
    )

    prorate_vat = fields.Float(
        string='Prorate Vat',
        default=0,
        store=True,
        readonly=True,
    )

    prorate_amount_2 = fields.Float(
        string='Prorate Amount See',
        default=0,
        store=True,
        readonly=True,
    )

    prorate_amount_exclude_2 = fields.Float(
        string='Prorate Amount Exclude Vat See',
        default=0,
        store=True,
        readonly=True,
    )

    prorate_vat_2 = fields.Float(
        string='Prorate Vat See',
        default=0,
        store=True,
        readonly=True,
    )

    is_type_discount_f_see = fields.Boolean(
        string="Type Discount F'See",
        default=False,
    )
