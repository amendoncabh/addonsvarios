# -*- coding: utf-8 -*-

from openerp import fields
from openerp import models



class PosConfig(models.Model):
    _inherit = 'pos.config'

    vip_discount_product_id = fields.Many2one(
        'product.product',
        string='VIP Discount Product',
        required=False,
    )
