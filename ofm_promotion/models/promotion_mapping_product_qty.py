# -*- coding: utf-8 -*-

from odoo import fields, models, api


class PromotionMappingProductQty(models.Model):
    _name = 'promotion.mapping.product.qty'

    def get_default_model_type(self):
        return self._context.get('model_type', False)

    def get_default_is_mapping_qty(self):
        return self._context.get('is_mapping_qty', False)

    model_type = fields.Selection(
        string="",
        selection=[
           ('condition', 'condition'),
           ('reward', 'reward'),
        ],
        required=True,
        default=get_default_model_type
    )

    promotion_condition_id = fields.Many2one(
        comodel_name="pos.promotion.condition",
        string="Pos Promotion Condition Reference",
        required=False,
        ondelete='cascade',
        index=True,
        copy=False
    )

    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product",
        required=True,
        index=True,
    )

    product_id_int = fields.Integer(
        string="Product ID",
        required=False,
        related='product_id.id',
    )

    barcode = fields.Char(
        string="Barcode",
        related="product_id.barcode",
        readonly=True,
    )

    qty = fields.Float(
        string="Quantity",
        required=True,
        default=1,
    )

    is_mapping_qty = fields.Boolean(
        string="",
        default=get_default_is_mapping_qty,
    )
