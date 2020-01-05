# -*- coding: utf-8 -*-

from openerp import fields, models


class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'
    pricelist_name = fields.Selection(
        [
             ('Normal', 'Normal'),
             ('Employee', 'Employee'),
        ],
    )

