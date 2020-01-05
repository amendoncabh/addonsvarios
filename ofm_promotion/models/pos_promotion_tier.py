# -*- coding: utf-8 -*-

from odoo import api
from odoo import fields
from odoo import models
import odoo.addons.decimal_precision as dp
import pytz
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo.exceptions import except_orm
from odoo.tools.translate import _


class PosPromotionTier(models.Model):
    _name = 'pos.promotion.tier'
    _order = 'start_tier, id'

    @api.depends('start_tier', 'tier_range')
    @api.multi
    def _compute_tier(self):
        for record in self:
            if record.start_tier and record.tier_range:
                record.end_tier = record.start_tier + record.tier_range - 1

    name = fields.Char(
        string="Name",
        required=True,
    )

    condition_type = fields.Selection(
        string="Condition Type",
        selection=[
            ('price', 'Price'),
            ('qty', 'Quantity'),
        ],
        required=False,
    )

    reward_type = fields.Selection(
        string="Reward Type",
        selection=[
            ('discount', 'Discount'),
            ('product', 'Product'),
            ('coupon', 'Coupon'),
        ],
        required=False,
    )

    start_tier = fields.Integer(
        string="Start Tier",
        required=False,
    )

    tier_range = fields.Integer(
        string="Range",
        required=False,
    )

    end_tier = fields.Integer(
        string="End Tier",
        readonly=True,
        compute="_compute_tier"
    )

    # priority_size = fields.Integer(
    #     string="Priority Size",
    #     default=9,
    #     required=False,
    # )

    tier_option_ids = fields.One2many(
        comodel_name="pos.promotion.tier.option",
        inverse_name="promotion_tier_id",
        string="Tier",
        required=False,
        ondelete='cascade',
    )

    # allow_mapping = fields.Boolean(
    #     string="Allow Mapping",
    # )

    # is_pricelist = fields.Boolean(
    #     string="Pricelist tier",
    #     default=False,
    # )

    @api.onchange('is_pricelist')
    def onchange_is_pricelist(self):
        if self.is_pricelist:
            self.condition_type = False
            self.reward_type = False
            self.tier_range = 1

    # def prepare_tier_options(self, values):
    #     if not values.get('tier_option_ids', False):
    #         start_tier = values.get('start_tier', self.start_tier)
    #         tier_range = values.get('tier_range', self.tier_range)
    #         if start_tier and tier_range:
    #             options = []
    #             for item in self.tier_option_ids:
    #                 item.unlink()
    #             for i in range(start_tier, start_tier + tier_range):
    #                 options.append((0, 0, {'name': str(i)}))
    #             values.update({
    #                 'tier_option_ids': options
    #             })

    # @api.multi
    # def write(self, values):
    #     # self.prepare_tier_options(values)
    #     return super(PosPromotionTier, self).write(values)


    # @api.model
    # def create(self, values):
    #     self.prepare_tier_options(values)
    #     return super(PosPromotionTier, self).create(values)


class PosPromotionTierOption(models.Model):
    _name = 'pos.promotion.tier.option'
    _order = "name"

    promotion_tier_id = fields.Many2one(
        comodel_name="pos.promotion.tier",
        string="Promotion Tier",
        required=False,
    )

    name = fields.Char(
        string="Tier",
        required=False,
    )


