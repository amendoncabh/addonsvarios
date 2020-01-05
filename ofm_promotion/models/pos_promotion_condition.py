# -*- coding: utf-8 -*-

from odoo import api
from odoo import fields
from odoo import models
import odoo.addons.decimal_precision as dp
from odoo.exceptions import except_orm, UserError
from odoo.tools.translate import _


class PosPromotionCondition(models.Model):
    _name = 'pos.promotion.condition'
    _order = 'condition_amount desc'

    @api.model
    def _default_sequence(self):
        self._get_promotion_type_selected()
        self.env.cr.execute('select COALESCE(sequence,0) from pos_promotion_condition order by sequence desc limit 1')

        sequence_returned = self.env.cr.fetchone()

        if sequence_returned is None:
            sequence_returned = 0
        else:
            sequence_returned = sequence_returned[0] + 1

        return sequence_returned

    def _get_default_promotion_type_selected(self):
        return self._context.get('promotion_type', False)

    def _get_default_condition_type_selected(self):
        condition_type_selected = self._context.get('condition_type', False)
        if not condition_type_selected:
            raise UserError(_("Please Select Rule"))
        return condition_type_selected

    def _get_default_reward_type_selected(self):
        return self._context.get('reward_type', False)

    def _get_default_promotion_condition_can_create(self):
        if not self._context.get('promotion_condition_can_create', False):
            raise except_orm(_('Error!'), _("Promotion Type \"Loop\" cannot add more than 1 condition."))

        return self._context.get('promotion_condition_can_create', False)

    @api.depends('promotion_id.promotion_name')
    @api.multi
    def _get_promotion_condition_name(self):
        for item in self:
            item.promotion_condition_name = item.promotion_id.promotion_name

    def get_apply_with_coupon_field(self):
        return self._context.get('apply_with_coupon')

    def get_default_reward_amount(self):
        reward_type = self.reward_type_selected or self._get_default_reward_type_selected()
        if reward_type == 'coupon':
            return 1
        else:
            return 0

    def get_default_reward_qty(self):
        reward_type = self.reward_type_selected or self._get_default_reward_type_selected()
        if reward_type == 'coupon':
            return 1
        else:
            return 0

    def get_default_condition_bill_limit(self):
        reward_type = self.reward_type_selected or self._get_default_reward_type_selected()
        if reward_type == 'coupon':
            return 1
        else:
            return 0

    @api.multi
    @api.depends('condition_mapping_product_qty_ids')
    def compute_condition_mapping_product_qty_flag(self):
        for record in self:
            record_len = len(record.condition_mapping_product_qty_ids)
            if record_len:
                record.condition_mapping_product_qty_flag = record_len
            else:
                record.condition_mapping_product_qty_flag = False

    @api.multi
    @api.depends('reward_mapping_product_qty_ids')
    def compute_reward_mapping_product_qty_flag(self):
        for record in self:
            record_len = len(record.reward_mapping_product_qty_ids)
            if record_len:
                record.reward_mapping_product_qty_flag = record_len
            else:
                record.reward_mapping_product_qty_flag = False

    sequence = fields.Integer(
        string='Sequence',
        default=_default_sequence,
        readonly=True,
    )

    promotion_condition_can_create = fields.Boolean(
        string='Promotion Condition Can Create',
        default=_get_default_promotion_condition_can_create,
        store=False,
    )

    promotion_id = fields.Many2one(
        comodel_name='pos.promotion',
        string='Promotion Reference',
        ondelete='cascade',
        index=True,
        copy=False
    )

    promotion_type_selected = fields.Char(
        string='Check Promotion Selected',
        default=_get_default_promotion_type_selected,
        compute='_get_promotion_type_selected',
        readonly=False,
    )

    condition_type_selected = fields.Char(
        string='Check Condition Selected',
        default=_get_default_condition_type_selected,
        compute='_get_condition_type_selected',
        readonly=False,
    )

    reward_type_selected = fields.Char(
        string='Check Reward Selected',
        default=_get_default_reward_type_selected,
        compute='_get_reward_type_selected',
        readonly=False,
    )

    promotion_condition_name = fields.Char(
        string='Condition Name',
        compute='_get_promotion_condition_name',
        translate=True,
        readonly=True,
        store=True,
    )

    apply_to_reward = fields.Boolean(
        string='Apply to Reward (Free Product)',
        help=_('make the cheapest product to be a reward'),
        default=False,
    )

    is_free_as_same_pid = fields.Boolean(
        string="Free with same PID",
    )

    condition_amount = fields.Float(
        string='Target Amount',
        default=0
    )

    condition_qty = fields.Integer(
        string='Target Quantity',
        default=0,
        compute='_get_condition_qty',
        readonly=False,
        store=False,
    )

    condition_price = fields.Float(
        string='Target Price',
        digits=dp.get_precision('Price'),
        default=0.0,
        compute='_get_condition_price',
        readonly=False,
        store=False,
    )

    condition_bill_limit = fields.Integer(
        string='Limit Amount per bill',
        default=get_default_condition_bill_limit
    )

    condition_product = fields.Selection(
        selection=[
            ('all', 'All Product'),
            ('brand', ' Product Brand'),
            ('category', ' Product Category'),
            ('dept', ' Product Dept'),
            ('sub_dept', 'Product Sub Dept'),
            ('manual', 'Manual Select (PID)')
        ],
        string="Product Type"
    )

    condition_brand_id = fields.Many2one(
        comodel_name="product.brand",
        string="Brand",
        index=True,
    )

    condition_categ_id = fields.Many2one(
        comodel_name='product.category',
        string='Category',
        index=True,
    )

    condition_dept = fields.Many2one(
        comodel_name='ofm.product.dept',
        string="Department",
        domain=[
            ('dept_parent_id', '=', False)
        ],
        index=True,
    )

    condition_sub_dept = fields.Many2one(
        comodel_name='ofm.product.dept',
        string="Sub Department",
        domain=[
            ('dept_parent_id', '!=', False)
        ],
        index=True,
    )

    is_exclude_product = fields.Boolean(
        string="Products Exception",
        default=False,
    )

    exclude_condition_product = fields.Selection(
        selection=[
            ('brand', ' Product Brand'),
            ('category', ' Product Category'),
            ('dept', ' Product Dept'),
            ('sub_dept', 'Product Sub Dept'),
            ('manual', 'Manual Select (PID)')
        ],
        string="Exclude Product Type"
    )

    exclude_condition_brand_id = fields.Many2one(
        comodel_name="product.brand",
        string="Exclude Brand",
        index=True,
    )

    exclude_condition_categ_id = fields.Many2one(
        comodel_name='product.category',
        string="Exclude Category",
        index=True,
    )

    exclude_condition_dept = fields.Many2one(
        comodel_name='ofm.product.dept',
        string="Exclude Department",
        domain=[
            ('dept_parent_id', '=', False)
        ],
        index=True,
    )

    exclude_condition_sub_dept = fields.Many2one(
        comodel_name='ofm.product.dept',
        string="Exclude Sub Department",
        domain=[
            ('dept_parent_id', '!=', False)
        ],
        index=True,
    )

    exclude_condition_manual_product = fields.Many2many(
        comodel_name="product.product",
        relation="pos_promotion_condition_exclude_product_product_rel",
        column1="pos_promotion_condition_id",
        column2="product_product_id",
        string="Select Products Exception",
        index=True,
    )

    exclude_condition_manual_text = fields.Text(
        string="Insert Exclude PID",
        required=False,
        store=False,
    )

    # TODO: 'simple' mapping and 'group' mapping
    condition_mapping_product_qty_ids = fields.One2many(
        comodel_name="promotion.mapping.product.qty",
        inverse_name="promotion_condition_id",
        string="Condition Product Detail",
        required=False,
        copy=True,
        domain=[('model_type', '=', 'condition')],
        index=True,
    )

    condition_mapping_product_qty_flag = fields.Char(
        string="Condition Product Detail",
        required=False,
        compute='compute_condition_mapping_product_qty_flag'
    )

    condition_mapping_product_text = fields.Text(
        string="Insert PID",
        required=False,
        store=False,
    )

    # TODO: 'simple' mapping and 'group' mapping
    reward_mapping_product_qty_ids = fields.One2many(
        comodel_name="promotion.mapping.product.qty",
        inverse_name="promotion_condition_id",
        string="Reward Product Detail",
        required=False,
        copy=True,
        domain=[('model_type', '=', 'reward')],
        index=True,
    )

    reward_mapping_product_qty_flag = fields.Char(
        string="Reward Product Detail",
        required=False,
        compute='compute_reward_mapping_product_qty_flag'
    )

    reward_mapping_product_text = fields.Text(
        string="Insert PID",
        required=False,
        store=False,
    )

    reward_discount_percentage = fields.Boolean(
        string='Percentage'
    )

    reward_amount = fields.Float(
        string='Reward Amount',
        default=1.0,
    )

    reward_qty = fields.Integer(
        string='Free Quantity',
        default=get_default_reward_qty,
        compute='_get_reward_qty',
        readonly=False,
        store=False,
    )

    reward_price = fields.Float(
        string='Discount Price',
        digits=dp.get_precision('Price'),
        default=0.0,
        compute='_get_reward_price',
        readonly=False,
        store=False,
    )

    reward_max_discount = fields.Float(
        string='Maximum Discount (THB)',
        help=_('set 0 to disable'),
        digits=dp.get_precision('Price'),
        default=0.0,
        readonly=False,
    )

    is_select_product_discount = fields.Boolean(
        string="Products Selection",
        default=False,
        help=_("Give Discount to the cheapest product on the products selection "
               "depend on a number of promotion that customer get"),
    )

    reward_product = fields.Selection(
        selection=[
            ('brand', ' Product Brand'),
            ('category', ' Product Category'),
            ('dept', ' Product Dept'),
            ('sub_dept', 'Product Sub Dept'),
            ('manual', 'Manual Select (PID)')
        ],
        string="Product Type"
    )

    reward_categ_id = fields.Many2one(
        comodel_name='product.category',
        string='Category',
        ondelete='cascade',
        index=True,
        help="Specify a product category if this rule only applies to products belonging "
             "to this category or its children categories. Keep empty otherwise.")

    reward_brand_id = fields.Many2one(
        comodel_name="product.brand",
        string="Brand",
        index=True,
    )

    reward_dept = fields.Many2one(
        comodel_name='ofm.product.dept',
        string="Department",
        required=False,
        domain=[
            ('dept_parent_id', '=', False)
        ],
        index=True,
    )

    reward_sub_dept = fields.Many2one(
        comodel_name='ofm.product.dept',
        string="Sub Department",
        required=False,
        domain=[
            ('dept_parent_id', '!=', False)
        ],
        index=True,
    )

    is_exclude_reward = fields.Boolean(
        string="Reward Products Exception",
        default=False,
    )

    exclude_reward_product = fields.Selection(
        selection=[
            ('brand', ' Product Brand'),
            ('category', ' Product Category'),
            ('dept', ' Product Dept'),
            ('sub_dept', 'Product Sub Dept'),
            ('manual', 'Manual Select (PID)')
        ],
        string="Exclude Reward Product Type"
    )

    exclude_reward_brand_id = fields.Many2one(
        comodel_name="product.brand",
        string="Exclude Reward Brand",
        index=True,
    )

    exclude_reward_categ_id = fields.Many2one(
        comodel_name='product.category',
        string="Exclude Reward Category",
        index=True,
    )

    exclude_reward_dept = fields.Many2one(
        comodel_name='ofm.product.dept',
        string="Exclude Reward Department",
        domain=[
            ('dept_parent_id', '=', False)
        ],
        index=True,
    )

    exclude_reward_sub_dept = fields.Many2one(
        comodel_name='ofm.product.dept',
        string="Exclude Reward Sub Department",
        domain=[
            ('dept_parent_id', '!=', False)
        ],
        index=True,
    )

    exclude_reward_manual_product = fields.Many2many(
        comodel_name="product.product",
        relation="pos_promotion_condition_exclude_reward_product_rel",
        column1="pos_promotion_condition_id",
        column2="product_product_id",
        string="Select Reward Products Exception",
        index=True,
    )

    exclude_reward_manual_text = fields.Text(
        string="Insert Exclude PID",
        required=False,
        store=False,
    )

    # coupon_id = fields.Many2one(
    #     comodel_name='product.product',
    #     string='Coupon',
    #     domain=[('is_coupon', '=', True), ('is_coupon_confirm', '=', True)],
    # )

    # coupon_ids = fields.Many2many(
    #     comodel_name="product.product",
    #     relation="pos_promotion_condition_product_coupon_rel",
    #     column1="pos_promotion_condition_id",
    #     column2="product_product_id",
    #     string="Coupon",
    #     domain=[('is_coupon', '=', True), ('is_coupon_confirm', '=', True)],
    #     index=True,
    # )

    is_condition_mapping_qty = fields.Boolean(
        string='Mapping Qty',
        default=False,
    )

    is_reward_mapping_qty = fields.Boolean(
        string='Mapping Qty',
        default=False,
    )

    condition_coupon_type = fields.Selection(
        string="Coupon Type",
        selection=[
            ('single', 'Single'),
            ('multi', 'Multi'),
        ],
        default="single",
    )

    condition_coupon_product_id = fields.Many2one(
        comodel_name="product.product",
        string="Coupon",
        required=False,
    )

    reward_coupon_type = fields.Selection(
        string="Coupon Type",
        selection=[
            ('single', 'Single'),
            ('multi', 'Multi'),
        ],
        default="single",
    )

    reward_coupon_product_id = fields.Many2one(
        comodel_name="product.product",
        string="Coupon",
        required=False,
    )

    apply_with_coupon = fields.Selection(
        string="Apply with coupon",
        related="promotion_id.apply_with_coupon",
        store=False,
        default=get_apply_with_coupon_field,
    )

    # @api.model
    # def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
    #     promotion_type = self._context.get('promotion_type', False)
    #     if promotion_type:
    #         if view_type == 'form':
    #             if promotion_type == 'step':
    #                 view_id = self.env.ref('ofm_promotion.promotion_step_condition_form_view').id
    #             elif promotion_type == 'loop':
    #                 view_id = self.env.ref('ofm_promotion.promotion_loop_condition_form_view').id
    #             # elif promotion_type == 'mapping':
    #             #     view_id = self.env.ref('ofm_promotion.promotion_mapping_condition_form_view').id
    #
    #     return super(PosPromotionCondition, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar
    #                                                               , submenu=submenu)

    @api.multi
    def _get_condition_type_selected(self):
        for item in self:
            item.condition_type_selected = item._context.get('condition_type')

    @api.multi
    def _get_promotion_type_selected(self):
        for item in self:
            item.promotion_type_selected = item._context.get('promotion_type', False)

    @api.multi
    def _get_reward_type_selected(self):
        for item in self:
            item.reward_type_selected = item._context.get('reward_type', False)

    @api.multi
    def _get_condition_qty(self):
        for item in self:
            if item.promotion_id.condition_type == 'qty':
                item.condition_qty = item.condition_amount

    @api.multi
    def _get_condition_price(self):
        for item in self:
            if item.promotion_id.condition_type == 'price':
                item.condition_price = item.condition_amount

    @api.multi
    def _get_reward_qty(self):
        for item in self:
            if item.promotion_id.reward_type in ('product', 'coupon'):
                item.reward_qty = item.reward_amount

    @api.multi
    def _get_reward_price(self):
        for item in self:
            if item.promotion_id.reward_type == 'discount':
                item.reward_price = item.reward_amount

    @api.onchange('apply_to_reward')
    def on_change_apply_to_reward(self):
        if self.apply_to_reward:
            self.reward_product = False
            self.exclude_reward_product = False
        self.is_free_as_same_pid = False

    @api.onchange('is_free_as_same_pid')
    def on_change_is_free_as_same_pid(self):
        if self.is_free_as_same_pid:
            self.is_condition_mapping_qty = False

    @api.onchange('is_select_product_discount')
    def onchange_is_select_product_discount(self):
        if not self.is_select_product_discount:
            self.reward_product = False
            self.exclude_reward_product = False

    @api.onchange('condition_qty')
    def onchange_condition_qty(self):
        self.condition_amount = self.condition_qty

    @api.onchange('condition_price')
    def onchange_condition_price(self):
        self.condition_amount = self.condition_price

    @api.onchange('reward_qty', 'reward_price')
    def onchange_reward_qty(self):
        reward_type = self.reward_type_selected or self._get_default_reward_type_selected()
        if reward_type in ('product', 'coupon'):
            self.reward_amount = self.reward_qty
        else:
            self.reward_amount = self.reward_price

    @api.onchange('condition_product')
    def onchange_condition_clear_product(self):
        self.condition_brand_id = False
        self.condition_categ_id = False
        self.condition_dept = False
        self.condition_sub_dept = False
        self.condition_mapping_product_qty_ids = [(6, 0, [])]

        if self.condition_product == 'manual':
            self.is_exclude_product = False

    @api.onchange('reward_product')
    def onchange_reward_clear_product(self):
        self.is_reward_coupon = False
        self.reward_brand_id = False
        self.reward_categ_id = False
        self.reward_dept = False
        self.reward_sub_dept = False
        self.reward_mapping_product_qty_ids = [(6, 0, [])]

        if self.reward_product == 'manual':
            self.is_exclude_reward = False

    @api.onchange('reward_discount_percentage')
    def onchange_reward_discount_percentage(self):
        self.reward_max_discount = 0

    @api.onchange('is_reward_coupon')
    def onchange_is_reward_coupon(self):
        self.is_exclude_product = False

    @api.onchange('is_exclude_product')
    def onchange_is_exclude_product(self):
        self.exclude_condition_product = False

    @api.onchange('exclude_condition_product')
    def onchange_exclude_condition_product(self):
        self.exclude_condition_brand_id = False
        self.exclude_condition_categ_id = False
        self.exclude_condition_dept = False
        self.exclude_condition_sub_dept = False
        self.exclude_condition_manual_product = [(6, 0, [])]

    @api.onchange('is_exclude_reward')
    def onchange_is_exclude_reward(self):
        self.exclude_reward_product = False

    @api.onchange('exclude_reward_product')
    def onchange_exclude_reward_product(self):
        self.exclude_reward_brand_id = False
        self.exclude_reward_categ_id = False
        self.exclude_reward_dept = False
        self.exclude_reward_sub_dept = False
        self.exclude_reward_manual_product = [(6, 0, [])]

    @api.onchange('is_condition_mapping_qty')
    def onchange_condition_mapping_product_qty_ids(self):
        for item in self.condition_mapping_product_qty_ids:
            item.is_mapping_qty = self.is_condition_mapping_qty
            if self.is_condition_mapping_qty is False:
                item.qty = 1
            else:
                self.condition_qty = 0

    @api.onchange('is_reward_mapping_qty')
    def onchange_reward_mapping_product_qty_ids(self):
        for item in self.reward_mapping_product_qty_ids:
            item.is_mapping_qty = self.is_reward_mapping_qty
            if self.is_reward_mapping_qty is False:
                item.qty = 1
            else:
                self.reward_qty = 0

    @api.onchange('condition_coupon_type')
    def onchange_condition_coupon_type(self):
        self.condition_coupon_product_id = False

    @api.onchange('reward_coupon_type')
    def onchange_condition_coupon_type(self):
        self.reward_coupon_product_id = False

    @api.onchange('condition_mapping_product_text')
    def onchange_condition_mapping_product_text(self):
        if self.condition_mapping_product_text and len(self.condition_mapping_product_text.strip()):
            pids = set()
            for line in self.condition_mapping_product_text.strip().splitlines():
                for pid in line.split(','):
                    pid = pid.strip()
                    if len(pid):
                        pids.add(pid)

            if len(pids):
                query_str = """
                    select id, default_code
                    from product_product
                    where active = true
                    and default_code in %s
                """

                self._cr.execute(query_str, (tuple(list(pids)),))

                products = self._cr.dictfetchall()

                search_pids = set()
                if len(products):
                    mapping_product_ids = []
                    for product in products:
                        mapping_product_ids.append(
                            (0, 0, {
                                'model_type': 'condition',
                                'product_id': product['id'],
                                'qty': 0
                            })
                        )
                        search_pids.add(product['default_code'])
                    self.condition_mapping_product_qty_ids = mapping_product_ids

                for pid in pids:
                    if pid not in search_pids:
                        self.env.user.notify_warning(
                            "Warning",
                            str(pid) + ': Not Found',
                            True
                        )

                del pids, search_pids, products
            self.condition_mapping_product_text = False

    @api.onchange('reward_mapping_product_text')
    def onchange_reward_mapping_product_text(self):
        if self.reward_mapping_product_text and len(self.reward_mapping_product_text.strip()):
            pids = set()
            for line in self.reward_mapping_product_text.strip().splitlines():
                for pid in line.split(','):
                    pid = pid.strip()
                    if len(pid):
                        pids.add(pid)

            if len(pids):
                query_str = """
                        select id, default_code
                        from product_product
                        where active = true
                        and default_code in %s
                    """

                self._cr.execute(query_str, (tuple(list(pids)),))

                products = self._cr.dictfetchall()

                search_pids = set()
                if len(products):
                    mapping_product_ids = []
                    for product in products:
                        mapping_product_ids.append(
                            (0, 0, {
                                'model_type': 'reward',
                                'product_id': product['id'],
                                'qty': 0
                            })
                        )
                        search_pids.add(product['default_code'])
                    self.reward_mapping_product_qty_ids = mapping_product_ids

                for pid in pids:
                    if pid not in search_pids:
                        self.env.user.notify_warning(
                            "Warning",
                            str(pid) + ': Not Found',
                            True
                        )

                del pids, search_pids, products
            self.reward_mapping_product_text = False

    @api.onchange('exclude_condition_manual_text')
    def onchange_exclude_condition_manual_text(self):
        if self.exclude_condition_manual_text and len(self.exclude_condition_manual_text.strip()):
            pids = set()
            for line in self.exclude_condition_manual_text.strip().splitlines():
                for pid in line.split(','):
                    pid = pid.strip()
                    if len(pid):
                        pids.add(pid)

            if len(pids):
                query_str = """
                    select id, default_code
                    from product_product
                    where active = true
                    and default_code in %s
                """

                self._cr.execute(query_str, (tuple(list(pids)),))

                products = self._cr.dictfetchall()

                search_pids = set()
                if len(products):
                    product_ids = []
                    for product in products:
                        product_ids.append(product['id'])
                        search_pids.add(product['default_code'])
                    self.exclude_condition_manual_product = self.env['product.product'].browse(product_ids)

                for pid in pids:
                    if pid not in search_pids:
                        self.env.user.notify_warning(
                            "Warning",
                            str(pid) + ': Not Found',
                            True
                        )

                del pids, search_pids, products
            self.exclude_condition_manual_text = False

    @api.onchange('exclude_reward_manual_text')
    def onchange_exclude_reward_manual_text(self):
        if self.exclude_reward_manual_text and len(self.exclude_reward_manual_text.strip()):
            pids = set()
            for line in self.exclude_reward_manual_text.strip().splitlines():
                for pid in line.split(','):
                    pid = pid.strip()
                    if len(pid):
                        pids.add(pid)

            if len(pids):
                query_str = """
                        select id, default_code
                        from product_product
                        where active = true
                        and default_code in %s
                    """

                self._cr.execute(query_str, (tuple(list(pids)),))

                products = self._cr.dictfetchall()

                search_pids = set()
                if len(products):
                    product_ids = []
                    for product in products:
                        product_ids.append(product['id'])
                        search_pids.add(product['default_code'])
                    self.exclude_reward_manual_product = self.env['product.product'].browse(product_ids)

                for pid in pids:
                    if pid not in search_pids:
                        self.env.user.notify_warning(
                            "Warning",
                            str(pid) + ': Not Found',
                            True
                        )

                del pids, search_pids, products
            self.exclude_reward_manual_text = False

    # def update_mapping_product_qty(self, vals):
    #     condition_mapping_product_qty_ids = vals.get('condition_mapping_product_qty_ids', False)
    #     reward_mapping_product_qty_ids = vals.get('reward_mapping_product_qty_ids', False)
    #     condition_manual_product_ids = vals.get('condition_manual_product_ids', False)
    #
    #     if condition_mapping_product_qty_ids:
    #         for condition_mapping_product_qty in condition_mapping_product_qty_ids:
    #             if condition_mapping_product_qty[0] == 0:
    #                 condition_mapping_product_qty[2]['model_type'] = 'condition_mapping'
    #
    #         vals['condition_mapping_product_qty_ids'] = condition_mapping_product_qty_ids
    #
    #     if condition_manual_product_ids:
    #         for condition_manual_product in condition_manual_product_ids:
    #             if condition_manual_product[0] == 0:
    #                 condition_manual_product[2]['model_type'] = 'condition_manual_product'
    #
    #         vals['condition_manual_product_ids'] = condition_manual_product_ids
    #
    #     if reward_mapping_product_qty_ids:
    #         for reward_mapping_product_qty in reward_mapping_product_qty_ids:
    #             if reward_mapping_product_qty[0] == 0:
    #                 reward_mapping_product_qty[2]['model_type'] = 'reward'
    #
    #         vals['reward_mapping_product_qty_ids'] = reward_mapping_product_qty_ids
    #
    #     return vals

    def check_delete_manual_product(self):
        if self.condition_product != 'manual':
            self.condition_mapping_product_qty_ids.unlink()

        if self.reward_product != 'manual':
            self.reward_mapping_product_qty_ids.unlink()

    @api.multi
    def create(self, vals):
        self.check_delete_manual_product()
        # vals = self.update_mapping_product_qty(vals)
        super(PosPromotionCondition, self).create(vals)

    @api.multi
    def write(self, vals):
        self.check_delete_manual_product()
        # vals = self.update_mapping_product_qty(vals)
        super(PosPromotionCondition, self).write(vals)
