# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
import csv
from StringIO import StringIO


class ImportPromotion(models.TransientModel):
    _name = 'import.promotion.wizard'
    _description = "Import Promotion"

    binary_data = fields.Binary(
        string="CSV File",
        required=True,
    )

    filename = fields.Char(
        string="File Name",
        required=False,
    )

    def create_promotion_condition(self,
                                   list_condition_mapping_product_qty,
                                   list_reward_mapping_product_qty,
                                   list_condition_except_product,
                                   list_reward_except_product,
                                   dict_promotion_condition,
                                   promotion_condition_obj,
                                   main_promotion_condition_can_create,
                                   main_condition_type):
        if list_condition_mapping_product_qty:
            dict_promotion_condition['condition_mapping_product_qty_ids'] = \
                [(0, 0, x) for x in list_condition_mapping_product_qty]

        if list_reward_mapping_product_qty:
            dict_promotion_condition['reward_mapping_product_qty_ids'] = \
                [(0, 0, x) for x in list_reward_mapping_product_qty]

        if list_condition_except_product:
            dict_promotion_condition['exclude_condition_manual_product'] = \
                [(6, 0, list_condition_except_product)]

        if list_reward_except_product:
            dict_promotion_condition['exclude_reward_manual_product'] = \
                [(6, 0, list_reward_except_product)]

        promotion_condition_obj.with_context(
            promotion_condition_can_create=main_promotion_condition_can_create,
            condition_type=main_condition_type,
        ).create(dict_promotion_condition)

    @api.multi
    def action_import_promotion(self):
        for item in self:
            active_id = item._context['active_id']
            promotion_obj = item.env[item._context['active_model']].search([('id', '=', active_id)])
            promotion_condition_obj = item.env['pos.promotion.condition']
            data = StringIO(item.binary_data.decode('base64'))

            product_obj = item.env['product.product']
            brand_obj = item.env['product.brand']
            category_obj = item.env['product.category']
            product_dept_obj = item.env['ofm.product.dept']

            main_condition_type = promotion_obj.condition_type
            main_reward_type = promotion_obj.reward_type
            main_promotion_condition_can_create = promotion_obj.promotion_condition_can_create
            main_promotion_type = promotion_obj.promotion_type

            dict_promotion_condition = {}
            list_condition_mapping_product_qty = []
            list_reward_mapping_product_qty = []
            list_condition_except_product = []
            list_reward_except_product = []

            check_promotion_condiiton_number = 1
            create_time = 0

            reader = csv.reader(
                data,
                delimiter=':'
            )

            next(reader)

            for row in reader:
                promotion_condiiton_number,\
                is_apply_to_reward,\
                condition_price,\
                condition_qty,\
                condition_bill_limit,\
                condition_product,\
                condition_brand_id,\
                condition_categ_id,\
                condition_dept,\
                condition_sub_dept,\
                condition_manual_product,\
                is_condition_mapping_qty,\
                condition_mapping_qty,\
                is_exclude_product,\
                exclude_condition_product,\
                exclude_condition_brand_id,\
                exclude_condition_categ_id,\
                exclude_condition_dept,\
                exclude_condition_sub_dept,\
                exclude_condition_manual_product,\
                is_reward_discount_percentage,\
                reward_discount,\
                reward_max_discount,\
                reward_qty,\
                is_select_product_discount,\
                reward_product,\
                reward_brand_id,\
                reward_categ_id,\
                reward_dept,\
                reward_sub_dept,\
                reward_manual_product,\
                is_reward_mapping_qty,\
                reward_mapping_qty,\
                is_reward_coupon,\
                is_exclude_reward,\
                exclude_reward_product,\
                exclude_reward_brand_id,\
                exclude_reward_categ_id,\
                exclude_reward_dept,\
                exclude_reward_sub_dept,\
                exclude_reward_manual_product = row[0].split(',')

                # Check Create

                if main_promotion_type == 'loop'\
                   and (len(promotion_obj.promotion_condition_ids) + create_time) == 1:
                    main_promotion_condition_can_create = False

                if check_promotion_condiiton_number != int(promotion_condiiton_number):
                    item.create_promotion_condition(list_condition_mapping_product_qty,
                                                    list_reward_mapping_product_qty,
                                                    list_condition_except_product,
                                                    list_reward_except_product,
                                                    dict_promotion_condition,
                                                    promotion_condition_obj,
                                                    main_promotion_condition_can_create,
                                                    main_condition_type)

                    create_time += 1
                    check_promotion_condiiton_number += 1

                    dict_promotion_condition = {}
                    list_condition_mapping_product_qty = []
                    list_reward_mapping_product_qty = []
                    list_condition_except_product = []
                    list_reward_except_product = []

                # Main Condition

                if len(dict_promotion_condition) == 0:
                    dict_promotion_condition = {
                        'promotion_id': active_id,

                        # Condition
                        'condition_product': condition_product,
                        'is_condition_mapping_qty': True if is_condition_mapping_qty == 'yes' else False,
                        'is_exclude_product': True if is_exclude_product == 'yes' else False,
                        'condition_bill_limit': 0 if main_promotion_type == 'step' else condition_bill_limit,

                        # Reward
                        'reward_product': reward_product,
                        'is_reward_mapping_qty': True if is_reward_mapping_qty == 'yes' else False,
                        'is_exclude_reward': True if is_exclude_reward == 'yes' else False,
                    }

                    if main_condition_type == 'qty':
                        dict_promotion_condition.update({
                            'condition_amount': 0 if is_condition_mapping_qty == 'yes' else condition_qty,
                        })
                        if main_reward_type == 'product':
                            dict_promotion_condition.update({
                                'apply_to_reward': True if is_apply_to_reward == 'yes' else False,
                            })
                    elif main_condition_type == 'price':
                        dict_promotion_condition.update({
                            'condition_amount': 0 if is_condition_mapping_qty == 'yes' else condition_price,
                        })

                    if main_reward_type == 'product':
                        dict_promotion_condition.update({
                            'reward_amount': 0 if is_condition_mapping_qty == 'yes' else reward_qty,
                        })
                    elif main_reward_type == 'discount':
                        dict_promotion_condition.update({
                            'reward_discount_percentage': True if is_reward_discount_percentage == 'yes' else False,
                            'reward_amount': 0 if is_condition_mapping_qty == 'yes' else reward_discount,
                            'is_select_product_discount': True if is_select_product_discount == 'yes' else False,
                        })

                        if is_reward_discount_percentage == 'yes':
                            dict_promotion_condition.update({
                                'reward_max_discount': reward_max_discount,
                            })

                    if condition_product == 'brand':
                        dict_promotion_condition['condition_brand_id'] = \
                            brand_obj.search([('ofm_brand_id', '=', condition_brand_id)], limit=1).id
                    elif condition_product == 'category':
                        condition_cat_id, condition_sub_cat_id = condition_categ_id.split('-')

                        dict_promotion_condition['condition_categ_id'] = \
                            category_obj.search([
                                ('cat_id', '=', condition_cat_id),
                                ('sub_cat_id', '=', condition_sub_cat_id),
                            ], limit=1).id
                    elif condition_product in ('dept', 'sub_dept'):
                        dict_promotion_condition['condition_dept'] = \
                            product_dept_obj.search([
                                ('ofm_dept_id', '=', condition_dept),
                                ('ofm_sub_dept_id', '=', '9999'),
                            ], limit=1).id

                        if condition_product == 'sub_dept':
                            condition_sub_dept_id, condition_class_id, condition_sub_class_id = \
                                condition_sub_dept.split('-')

                            dict_promotion_condition['condition_sub_dept'] = \
                                product_dept_obj.search([
                                    ('ofm_sub_dept_id', '=', condition_sub_dept_id),
                                    ('ofm_class_id', '=', condition_class_id),
                                    ('ofm_sub_class_id', '=', condition_sub_class_id),
                                ], limit=1).id

                    if is_exclude_product == 'yes':
                        dict_promotion_condition['exclude_condition_product'] = exclude_condition_product

                        if exclude_condition_product == 'brand':
                            dict_promotion_condition['exclude_condition_brand_id'] = \
                                brand_obj.search([('ofm_brand_id', '=', exclude_condition_brand_id)], limit=1).id
                        elif exclude_condition_product == 'category':
                            exclude_condition_cat_id, exclude_condition_sub_cat_id = \
                                exclude_condition_categ_id.split('-')

                            dict_promotion_condition['exclude_condition_categ_id'] = \
                                category_obj.search([
                                    ('cat_id', '=', exclude_condition_cat_id),
                                    ('sub_cat_id', '=', exclude_condition_sub_cat_id),
                                ], limit=1).id
                        elif exclude_condition_product in ('dept', 'sub_dept'):
                            dict_promotion_condition['exclude_condition_dept'] = \
                                product_dept_obj.search([
                                    ('ofm_dept_id', '=', exclude_condition_dept),
                                    ('ofm_sub_dept_id', '=', '9999'),
                                ], limit=1).id

                            if exclude_condition_product == 'sub_dept':
                                exclude_condition_sub_dept_id, exclude_condition_class_id, \
                                exclude_condition_sub_class_id = exclude_condition_sub_dept.split('-')

                                dict_promotion_condition['exclude_condition_sub_dept'] = \
                                    product_dept_obj.search([
                                        ('ofm_sub_dept_id', '=', exclude_condition_sub_dept_id),
                                        ('ofm_class_id', '=', exclude_condition_class_id),
                                        ('ofm_sub_class_id', '=', exclude_condition_sub_class_id),
                                    ], limit=1).id

                    if is_apply_to_reward != 'yes':

                        if reward_product == 'brand':
                            dict_promotion_condition['reward_brand_id'] = \
                                brand_obj.search([('ofm_brand_id', '=', reward_brand_id)], limit=1).id
                        elif reward_product == 'category':
                            reward_cat_id, reward_sub_cat_id = reward_categ_id.split('-')

                            dict_promotion_condition['reward_categ_id'] = \
                                category_obj.search([
                                    ('cat_id', '=', reward_cat_id),
                                    ('sub_cat_id', '=', reward_sub_cat_id),
                                ], limit=1).id
                        elif reward_product in ('dept', 'sub_dept'):
                            dict_promotion_condition['reward_dept'] = \
                                product_dept_obj.search([
                                    ('ofm_dept_id', '=', reward_dept),
                                    ('ofm_sub_dept_id', '=', '9999'),
                                ], limit=1).id

                            if reward_product == 'sub_dept':
                                reward_sub_dept_id, reward_class_id, reward_sub_class_id = \
                                    reward_sub_dept.split('-')

                                dict_promotion_condition['reward_sub_dept'] = \
                                    product_dept_obj.search([
                                        ('ofm_sub_dept_id', '=', reward_sub_dept_id),
                                        ('ofm_class_id', '=', reward_class_id),
                                        ('ofm_sub_class_id', '=', reward_sub_class_id),
                                    ], limit=1).id

                        if is_exclude_reward == 'yes':
                            dict_promotion_condition['exclude_reward_product'] = exclude_reward_product

                            if exclude_reward_product == 'brand':
                                dict_promotion_condition['exclude_reward_brand_id'] = \
                                    brand_obj.search([('ofm_brand_id', '=', exclude_reward_brand_id)], limit=1).id
                            elif exclude_reward_product == 'category':
                                exclude_reward_cat_id, exclude_reward_sub_cat_id = exclude_reward_categ_id.split('-')

                                dict_promotion_condition['exclude_reward_categ_id'] = \
                                    category_obj.search([
                                        ('cat_id', '=', exclude_reward_cat_id),
                                        ('sub_cat_id', '=', exclude_reward_sub_cat_id),
                                    ], limit=1).id
                            elif exclude_reward_product in ('dept', 'sub_dept'):
                                dict_promotion_condition['exclude_reward_dept'] = \
                                    product_dept_obj.search([
                                        ('ofm_dept_id', '=', exclude_reward_dept),
                                        ('ofm_sub_dept_id', '=', '9999'),
                                    ], limit=1).id

                                if exclude_reward_product == 'sub_dept':
                                    exclude_reward_sub_dept_id, exclude_reward_class_id, \
                                    exclude_reward_sub_class_id = exclude_reward_sub_dept.split('-')

                                    dict_promotion_condition['exclude_reward_sub_dept'] = \
                                        product_dept_obj.search([
                                            ('ofm_sub_dept_id', '=', exclude_reward_sub_dept_id),
                                            ('ofm_class_id', '=', exclude_reward_class_id),
                                            ('ofm_sub_class_id', '=', exclude_reward_sub_class_id),
                                        ], limit=1).id

                if condition_product == 'manual' and condition_manual_product:
                    list_condition_mapping_product_qty.append({
                        'product_id': product_obj.search([('default_code', '=', condition_manual_product)]).id,
                        'model_type': 'condition',
                        'qty': condition_mapping_qty if is_condition_mapping_qty == 'yes' else 1,
                        'is_mapping_qty': True if is_condition_mapping_qty == 'yes' else False,
                    })

                if reward_product == 'manual' and reward_manual_product:
                    list_reward_mapping_product_qty.append({
                        'product_id': product_obj.search([('default_code', '=', reward_manual_product)]).id,
                        'model_type': 'reward',
                        'qty': reward_mapping_qty if is_reward_mapping_qty == 'yes' else 1,
                        'is_mapping_qty': True if is_reward_mapping_qty == 'yes' else False,
                    })

                # Exception Case Manual

                if all([
                        is_exclude_product == 'yes',
                        exclude_condition_product == 'manual',
                        exclude_condition_manual_product
                ]):
                    list_condition_except_product.append(
                        product_obj.search([('default_code', '=', exclude_condition_manual_product)]).id
                    )

                if all([
                        is_exclude_product == 'yes',
                        exclude_reward_product == 'manual',
                        exclude_reward_manual_product
                ]):
                    list_reward_except_product.append(
                        product_obj.search([('default_code', '=', exclude_reward_manual_product)]).id
                    )

            # Create Last Data
            item.create_promotion_condition(list_condition_mapping_product_qty,
                                            list_reward_mapping_product_qty,
                                            list_condition_except_product,
                                            list_reward_except_product,
                                            dict_promotion_condition,
                                            promotion_condition_obj,
                                            main_promotion_condition_can_create,
                                            main_condition_type)

        return {'type': 'ir.actions.act_window_close'}
