# -*- coding: utf-8 -*-

from odoo import api
from odoo import fields
from odoo import models


class Product(models.Model):
    _inherit = 'product.product'
    
    all_categories = fields.Char(compute="_get_all_categories")
    
    @api.one
    def _get_all_categories(self):
        self.all_categories = ''
        parent = self.categ_id.parent_id;
        parent_id = parent.id;
        loop_count = 0
        while parent_id:
            self.all_categories += str(parent_id) + ','
            parent_id = parent.parent_id.id
            parent = parent.parent_id;
            # prevent infinity loop
            loop_count += 1
            if(loop_count > 100):
                break
        self.all_categories += str(self.categ_id.id)

    price_by_branch_ids = fields.One2many(
        comodel_name="pos.product.template.line",
        inverse_name="product_id",
        string="Prices",
        required=False,
        readonly=True,
    )


class product_template(models.Model):
    _inherit = "product.template"

    exempt_pos_calculate = fields.Boolean(
        string="Exempt POS Calculate"
    )

    is_hold_sale = fields.Boolean(
        string="Hold Sale"
    )

