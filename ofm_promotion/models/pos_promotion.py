# -*- coding: utf-8 -*-

from odoo import api
from odoo import fields
from odoo import models
import pytz
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo.exceptions import except_orm
from odoo.tools.translate import _

PRIORITY_SIZE = [
    ('1', '1'),
    ('2', '2'),
    ('3', '3'),
    ('4', '4'),
    ('5', '5'),
    ('6', '6'),
    ('7', '7'),
    ('8', '8'),
    ('9', '9'),
]


class PosPromotion(models.Model):
    _name = 'pos.promotion'
    _inherit = ['promotion.week.mixin']
    _order = 'tier,priority,sequence,id'

    _sql_constraints = [
        ('name_uniq', 'unique (promotion_code)', "Promotion Code already exists !")
    ]

    @api.model
    def _default_sequence(self):
        self.env.cr.execute('select COALESCE(sequence,0) from pos_promotion order by sequence desc limit 1')

        sequence_returned = self.env.cr.fetchone()

        if sequence_returned is None:
            sequence_returned = 0
        else:
            sequence_returned = sequence_returned[0] + 1

        return sequence_returned

    @api.model
    def _default_promotion_name(self):
        return 'Promotion ' + str(self._default_sequence())

    @api.model
    def _default_date_start(self):
        tz = pytz.timezone(self.env.user.tz) if self.env.user.tz else pytz.utc  # get user timezone
        date_start = tz.localize(datetime.today())  # get today date
        date_start = date_start.replace(hour=0,minute=0,second=0)  # Set to 00:00:00 localtime
        date_start = date_start.astimezone(pytz.utc)  # Convert to UTC
        return date_start

    @api.model
    def _default_date_end(self):
        tz = pytz.timezone(self.env.user.tz) if self.env.user.tz else pytz.utc  # get user timezone
        date_end = tz.localize(datetime.today() + relativedelta(months=1))  # get today date
        date_end = date_end.replace(hour=23, minute=59, second=59)  # Set to 23:59:59 localtime
        date_end = date_end.astimezone(pytz.utc)  # Convert to UTC
        return date_end

    sequence = fields.Integer(
        string='Sequence',
        default=_default_sequence,
        readonly=True,
        copy=False,
    )

    branch_ids = fields.Many2many(
        comodel_name='pos.branch',
        relation='pos_branch_pos_promotion_rel',
        column1='pos_promotion_id',
        column2='pos_branch_id',
    )

    promotion_code = fields.Char(
        string='Promotion Code',
        required=True,
        copy=False,
    )

    promotion_name = fields.Char(
        string='Promotion Name',
        required=True,
        default=_default_promotion_name,
        copy=False,
    )

    bank_share = fields.Char(
        string='Bank',
    )

    company_share = fields.Char(
        string='Company',
    )

    vendor_share = fields.Char(
        string='Vendor',
    )

    is_best_deal = fields.Boolean(
        string="Include with Best deal",
        default=False,
    )

    is_channel_pos = fields.Boolean(
        string="POS",
        default=False,
    )

    is_channel_instore = fields.Boolean(
        string="In Store",
        default=False,
    )

    is_channel_dropship = fields.Boolean(
        string="Dropship",
        default=False,
    )

    internal_note = fields.Text(
        string="Internal Note",
        required=False,
    )

    promotion_segment = fields.Selection(
        selection=[
            ('mer', 'Merchandise'),
            ('mar', 'Marketing'),
        ],
        string='Promotion Segment',
        default='mer',
    )

    promotion_type = fields.Selection(
        selection=[
            ('step', 'Step'),
            ('loop', 'Loop'),
        ],
        string='Promotion Type',
        store=True,
        default='step',
    )

    tier_id = fields.Many2one(
        comodel_name="pos.promotion.tier",
        string="Rule",
        required=True,
    )

    tier_option_id = fields.Many2one(
        comodel_name="pos.promotion.tier.option",
        string="Tier",
        required=True,
    )

    tier = fields.Char(
        string="Tier",
        required=False,
        readonly=True,
        related='tier_option_id.name',
        store=True,
    )

    start_tier = fields.Integer(
        string="Start Tier",
        required=False,
        readonly=True,
        related='tier_id.start_tier',
    )

    priority = fields.Selection(
        string="Priority",
        selection=PRIORITY_SIZE,
        default=PRIORITY_SIZE[4][0],
        required=True,
    )

    is_exclude_tier = fields.Boolean(
        string="Exclude Tier",
        default=False,
    )

    exclude_tier_ids = fields.Many2many(
        comodel_name="pos.promotion.tier",
        relation="pos_promotion_pos_promotion_tier_rel",
        column1="promotion_id",
        column2="tier_id",
        string="Tier To Exclude",
    )

    condition_type = fields.Selection(
        string='Condition Type',
        selection=[
            ('price', 'Price'),
            ('qty', 'Quantity'),
        ],
        related='tier_id.condition_type',
        readonly=True,
        store=True,
    )

    condition_type_general = fields.Selection(
        selection=[
            ('price', 'Price'),
            ('qty', 'Quantity'),
        ],
        string='Condition Type',
        # compute='_get_condition_type_general',
        readonly=False,
        store=False,
    )

    condition_type_mapping = fields.Selection(
        selection=[
            ('qty', 'Quantity'),
        ],
        string='Condition Type',
        # compute='_get_condition_type_mapping',
        readonly=False,
        store=False,
    )

    reward_type = fields.Selection(
        string='Reward Type',
        default='discount',
        selection=[
            ('discount', 'Discount'),
            ('product', 'Product'),
            ('coupon', 'Coupon'),
        ],
        readonly=True,
        related='tier_id.reward_type',
        store=True,
    )


    date_start = fields.Datetime(
        string='Start Date',
        help="Starting date for promotion rule",
        required=True,
        default=_default_date_start,
    )

    date_end = fields.Datetime(
        string='End Date',
        help="Ending valid for promotion rule",
        required=True,
        default=_default_date_end,
    )

    is_custom_time = fields.Boolean(
        string="Set Time",
        default=False,
    )

    start_time = fields.Float(
        string='Start Time',
        help="Starting Time for promotion rule.\n"
             "For example, Start time set at 7:00, then promotion is not active before 6:59:59, while 07:00 is active",
        default=7,
    )

    end_time = fields.Float(
        string='End Time',
        help="Ending Time for promotion rule.\n"
             "For example, End time set at 21:00, then promotion is not active after 21:00, while 20:59:59 is active",
        default=21,
    )

    promotion_condition_ids = fields.One2many(
        comodel_name='pos.promotion.condition',
        inverse_name='promotion_id',
        string='Condition Detail',
        copy=True,
    )

    promotion_step_condition_ids = fields.One2many(
        comodel_name='pos.promotion.condition',
        inverse_name='promotion_id',
        string='Condition Detail',
    )

    promotion_loop_condition_ids = fields.One2many(
        comodel_name='pos.promotion.condition',
        inverse_name='promotion_id',
        string='Condition Detail',
    )

    promotion_mapping_condition_ids = fields.One2many(
        comodel_name='pos.promotion.condition',
        inverse_name='promotion_id',
        string='Condition Detail',
    )

    active = fields.Boolean(
        "Active",
        default=True,
    )

    promotion_condition_can_create = fields.Boolean(
        string='Promotion Condition Can Create',
        compute='check_promotion_condition_can_create',
    )

    apply_with_coupon = fields.Selection(
        string="Coupon",
        selection=[
            ('no', 'Non Coupon'),
            ('condition', 'Condition'),
            ('reward', 'Reward'),
        ],
        required=False,
        default='no',
    )

    apply_with_coupon_wo_reward = fields.Selection(
        string="Coupon",
        selection=[
            ('no', 'Non Coupon'),
            ('condition', 'Condition'),
        ],
        required=False,
        default='no',
    )

    apply_with_coupon_w_reward = fields.Selection(
        string="Coupon",
        selection=[
            ('no', 'Non Coupon'),
            ('condition', 'Condition'),
            ('reward', 'Reward'),
        ],
        required=False,
        readonly=True,
        default='reward',
    )

    @api.multi
    def name_get(self):
        result = []
        for record in self:
            result.append((record.id, record.promotion_name))
        return result

    # @api.multi
    # def _get_condition_type_general(self):
    #     for item in self:
    #         if not item.promotion_type == 'mapping':
    #             if item.condition_type:
    #                 item.condition_type_general = item.condition_type
    #             else:
    #                 item.condition_type_general = 'price'
    #
    # @api.multi
    # def _get_condition_type_mapping(self):
    #     for item in self:
    #         if item.promotion_type == 'mapping':
    #             if item.condition_type:
    #                 item.condition_type_mapping = item.condition_type
    #             else:
    #                 item.condition_type_mapping = 'qty'

    # @api.depends('promotion_type_w_mapping', 'promotion_type_wo_mapping')
    # @api.multi
    # def compute_promotion_type(self):
    #     for record in self:
    #         if record.allow_mapping:
    #             record.promotion_type = record.promotion_type_w_mapping
    #         else:
    #             record.promotion_type = record.promotion_type_wo_mapping

    @api.multi
    def check_promotion_condition_can_create(self):
        for rec in self:
            # if rec.promotion_type == 'loop' and len(rec.promotion_condition_ids._ids) > 0:
            #     rec.promotion_condition_can_create = False
            # else:
            #     rec.promotion_condition_can_create = True
            rec.promotion_condition_can_create = True

        return True

    def check_promotion_is_used(self):
        pos_order_line = self.env['pos.order.line'].search([('promotion_id', '=', self.id)])

        if pos_order_line:
            return True
        else:
            return False

    @api.onchange('promotion_segment')
    def onchange_promotion_segment(self):
        if self.promotion_segment == 'mer':
            self.is_best_deal = True
        elif self.promotion_segment == 'mar':
            self.is_best_deal = False

    @api.onchange('apply_with_coupon_w_reward', 'apply_with_coupon_wo_reward')
    def onchange_apply_with_coupon_reward(self):
        if self.reward_type == 'coupon':
            self.apply_with_coupon = self.apply_with_coupon_w_reward
        else:
            self.apply_with_coupon = self.apply_with_coupon_wo_reward

    @api.onchange('tier_id')
    def onchange_tier_id(self):
        if self.tier_id:
            self.tier_option_id = self.tier_id.tier_option_ids[0].id
        else:
            self.tier_option_id = False

        self.promotion_type = 'step'
        self.is_exclude_tier = False

    @api.onchange('is_exclude_tier')
    def onchagnge_is_exclude_tier(self):
        if not self.is_exclude_tier:
            self.exclude_tier_ids = [(6, 0, [])]

    @api.onchange('promotion_condition_ids')
    def onchange_promotion_condition_ids(self):
        self.check_promotion_condition_can_create()

    # @api.onchange('promotion_type')
    # def onchange_promotion_type(self):
    #     self.clear_promotion_condition_ids()
    #
    #     if self.promotion_type == 'mapping':
    #         if not self.condition_type_mapping:
    #             self.condition_type_mapping = 'qty'
    #     else:
    #         if not self.condition_type_general:
    #             self.condition_type_general = 'price'

    @api.onchange('condition_type')
    def onchange_condition_type_mapping(self):
        self.clear_promotion_condition_ids()

        for promotion_condition_id in self.promotion_condition_ids:
            promotion_condition_id.condition_type_selected = self.condition_type

    # @api.onchange('condition_type_general')
    # def onchange_condition_type_general(self):
    #     self.clear_promotion_condition_ids()
    #
    #     for promotion_condition_id in self.promotion_condition_ids:
    #         promotion_condition_id.promotion_type_selected = self.promotion_type
    #         promotion_condition_id.condition_type_selected = self.condition_type_general
    #         promotion_condition_id.reward_type_selected = self.reward_type
    #
    #         if self.condition_type_general == 'price':
    #             promotion_condition_id.condition_price = promotion_condition_id.condition_amount
    #         else:
    #             promotion_condition_id.condition_qty = promotion_condition_id.condition_amount
    #
    #         if self.reward_type == 'discount':
    #             promotion_condition_id.reward_price = promotion_condition_id.reward_amount
    #         else:
    #             promotion_condition_id.reward_qty = promotion_condition_id.reward_amount

    @api.onchange('reward_type')
    def onchange_reward_type(self):
        self.clear_promotion_condition_ids()

        if self.reward_type == 'coupon':
            self.apply_with_coupon = self.apply_with_coupon_w_reward
        else:
            self.apply_with_coupon = self.apply_with_coupon_wo_reward

        for promotion_condition_id in self.promotion_condition_ids:
            promotion_condition_id.promotion_type_selected = self.promotion_type

            promotion_condition_id.condition_type_selected = self.condition_type

            promotion_condition_id.reward_type_selected = self.reward_type

            if self.condition_type == 'price':
                promotion_condition_id.condition_price = promotion_condition_id.condition_amount
            else:
                promotion_condition_id.condition_qty = promotion_condition_id.condition_amount

            if self.reward_type == 'discount':
                promotion_condition_id.reward_price = promotion_condition_id.reward_amount
            else:
                promotion_condition_id.reward_qty = promotion_condition_id.reward_amount

    @api.onchange('date_start')
    def onchange_date_start(self):
        default_date_start = self._default_date_start()
        if self.date_start < default_date_start.strftime('%Y-%m-%d %H:%M:%S'):
            self.date_start = default_date_start
        if (self.date_start > self.date_end) and self.date_end:
            self.date_start = None

    @api.onchange('date_end')
    def onchange_date_end(self):
        if (self.date_start > self.date_end) and self.date_start:
            self.date_end = None

    @api.onchange('start_time')
    def onchange_start_time(self):
        if self.start_time:
            if self.start_time < 0:
                self.start_time = -self.start_time
            if self.start_time > 24:
                self.start_time = 24
            if self.end_time and self.start_time >= self.end_time:
                self.start_time = None

    @api.onchange('end_time')
    def onchange_end_time(self):
        if self.end_time:
            if self.end_time < 0:
                self.end_time = -self.end_time
            if self.end_time > 24:
                self.end_time = 24
            if self.start_time and self.start_time >= self.end_time:
                self.end_time = None

    @api.onchange('apply_with_coupon')
    def onchange_apply_with_coupon(self):
        self.clear_promotion_condition_ids()

    def clear_promotion_condition_ids(self):
        self.promotion_condition_ids = []
        self.promotion_step_condition_ids = [(6, 0, [])]
        self.promotion_loop_condition_ids = [(6, 0, [])]
        self.promotion_mapping_condition_ids = [(6, 0, [])]

        return True

    def promotion_name_check_duplicate(self, promotion_name):
        promotion_duplicate = self.env['pos.promotion'].search([
            ('id', '!=', self.id),
            ('promotion_name', '=', promotion_name),
        ])

        if promotion_duplicate:
            raise except_orm(_('Error!'), _("Promotion Name Can't Duplicate"))

    # def allow_update_fields(self, vals):
    #     allow_field = self.env['ir.config_parameter'].sudo().get_param('pos_promotion_update_field')
    #     allow_field = [field.strip() for field in allow_field.split(',')]
    #
    #     def check_existing_fields(values):
    #         for key in allow_field:
    #             if key in values:
    #                 return True
    #         return False
    #
    #     if check_existing_fields(vals):
    #         for val_update in vals.keys():
    #             if val_update not in allow_field:
    #                 vals.pop(val_update)
    #     else:
    #         raise except_orm(_('Error!'), _("This Promotion can't edit because it was used"))
    #     return vals

    @api.model
    def create(self, vals):
        self.promotion_name_check_duplicate(vals.get('promotion_name'))

        if not vals.get('is_channel_pos', False) \
                and not vals.get('is_channel_instore', False)\
                and not vals.get('is_channel_dropship', False):
            raise except_orm(_('Error!'), _("กรุณาเลือกช่องทางการใช้โปรโมชั่น"))

        if not vals.get('branch_ids', False):
            raise except_orm(_('Error!'), _("กรุณาเลือกสาขา"))

        promotion = super(PosPromotion, self).create(vals)

        return promotion

    @api.multi
    def write(self, vals):
        for item in self:
            # if item.check_promotion_is_used():
            #     vals = self.allow_update_fields(vals)

            item.promotion_name_check_duplicate(vals.get('promotion_name'))

            if vals.get('promotion_type', False):
                promotion_type = vals.get('promotion_type', False)
            else:
                promotion_type = item.promotion_type

        promotion = super(PosPromotion, self).write(vals)

        return promotion

    @api.multi
    def unlink(self):
        try:
            result = super(PosPromotion, self).unlink()
        except:
            raise except_orm(_("ไม่สามารถลบโปรโมชั่นที่ถูกใช้ไปแล้วได้"))

        return result
