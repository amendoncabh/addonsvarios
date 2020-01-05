# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
import random
import string

import logging

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_coupon = fields.Boolean(
        string="COUPON",
        readonly=True,
    )

    is_coupon_confirm = fields.Boolean(
        string="COUPON",
        readonly=True,
    )

    description = fields.Text(
        string="Description",
        required=False,
    )

    list_price = fields.Float(
        default=0.0,
    )


class ProductProduct(models.Model):
    _inherit = "product.product"

    barcode = fields.Char(
        size=15,
    )

    multi_coupon_ids = fields.One2many(
        comodel_name="multi.coupon",
        inverse_name="product_id",
        string="Multi Coupon",
        required=False,
        index=True,
        ondelete="cascade",
        readonly=True,
    )

    coupon_type = fields.Selection(
        string="Coupon Type",
        selection=[
            ('single', 'Single'),
            ('multi', 'Multi'),
        ],
        required=True,
        default="single",
    )

    coupon_limit = fields.Integer(
        string="Limit Coupon",
        required=False,
        default=0,
    )

    coupon_used_time = fields.Integer(
        string="Used Time",
        required=False,
        default=0,
    )

    @api.multi
    def enable_coupon(self):
        for record in self:
            digits = "".join([random.choice(string.digits) for i in xrange(5)])
            chars = "".join([random.choice(string.letters) for i in xrange(5)])

            merge_digits_chars = digits + chars

            merge_digits_chars = ''.join(random.sample(merge_digits_chars, len(merge_digits_chars)))
            record.product_tmpl_id.is_coupon_confirm = True
            # self.barcode = merge_digits_chars.upper()

        return True

    @api.multi
    def disable_coupon(self):
        for record in self:

            is_order_line_usage = record.env['pos.order.line'].search([
                ('product_id', '=', record.id)
            ])

            if is_order_line_usage:
                raise ValidationError(_("Coupon have usage Can't Disable"))
            else:
                record.product_tmpl_id.is_coupon_confirm = False
        return True

    @api.onchange('coupon_type')
    def onchange_coupon_type(self):
        if self.coupon_type == 'multi':
            self.coupon_limit = 0
            self.barcode = None

    @api.onchange('coupon_limit')
    def onchange_coupon_limit(self):
        if self.coupon_limit < self.coupon_used_time:
            self.coupon_limit = self.coupon_used_time

    @api.model
    def coupon_process(self):
        process_type = self._context.get('process_type', False)
        product_ids = self._context.get('product_ids', False)
        barcode = self._context.get('barcode', False)

        if not process_type or not product_ids:
            return {
                'status': 'fail',
                'message': 'Api fail',
            }

        return_dict = {}

        if process_type == 'receive':
            for product_id in product_ids:
                parameter_product_id = (
                    product_id,
                )

                self._cr.execute("""
                    select id as multi_coupon_id
                    from multi_coupon
                    where is_received is false
                        and is_reserved = false
                        and is_used is false
                        and is_canceled is false
                        and product_id = %s
                    order by id asc
                    limit 1
                """, parameter_product_id)

                multi_coupon_id_obj = self._cr.dictfetchall()

                if multi_coupon_id_obj:
                    parameter_multi_coupon_id = (
                        multi_coupon_id_obj[0]['multi_coupon_id'],
                    )

                    self._cr.execute("""
                        update multi_coupon
                        set is_received = true
                        where id = %s
                    """, parameter_multi_coupon_id)
                    self._cr.commit()

                    return_dict[product_id] = multi_coupon_id_obj[0]['multi_coupon_id']
                    
            if not len(return_dict):
                return_dict = {
                    'status': 'fail',
                    'message': 'Not found coupon.',
                }
            else:
                return_dict['status'] = 'success'
        elif process_type == 'reserve':
            for product_id in product_ids:
                if not barcode:
                    return {
                        'status': 'fail',
                        'message': 'Api fail',
                    }
                parameter_product_and_barcode = (
                    product_id,
                    barcode
                )

                self._cr.execute("""
                    select
                        id,
                        case 
                            when is_used then 'used'
                            when is_canceled then 'canceled'
                            when is_reserved then 'reserved'
                            else 'to_give'
                        end as status
                    from
                        multi_coupon
                    where
                        product_id = %s
                        and barcode = %s
                    limit 1
                """, parameter_product_and_barcode)

                multi_coupon_count_obj = self._cr.dictfetchall()

                if multi_coupon_count_obj[0]['status'] == 'to_give':
                    self._cr.execute("""
                        update multi_coupon
                        set is_reserved = true,
                        write_date = now() at time zone 'UTC'
                        where id = %s
                    """, (multi_coupon_count_obj[0]['id'],))
                    self._cr.commit()

                    return_dict = {
                        'status': 'success',
                    }
                elif multi_coupon_count_obj[0]['status'] == 'canceled':
                    return_dict = {
                        'status': 'fail',
                        'message': 'คูปองนี้ได้ถูกยกเลิกการใช้งานแล้ว',
                    }
                elif multi_coupon_count_obj[0]['status'] == 'used':
                    return_dict = {
                        'status': 'fail',
                        'message': 'คูปองนี้ได้ถูกใช้งานไปแล้ว',
                    }
                elif multi_coupon_count_obj[0]['status'] == 'reserved':
                    return_dict = {
                        'status': 'fail',
                        'message': 'คูปองนี้ได้มีการจองไปแล้ว',
                    }
                else:
                    return_dict = {
                        'status': 'fail',
                        'message': 'This coupon fail',
                    }

        elif process_type == 'unreserved':
            for product_id in product_ids:
                if not barcode:
                    return {
                        'status': 'fail',
                        'message': 'Api fail',
                    }

                parameter_product_and_barcode = (
                    product_id,
                    barcode
                )

                self._cr.execute("""
                    select count('') as row_count
                    from multi_coupon
                    where is_canceled = false
                        and product_id = %s
                        and barcode = %s
                    limit 1
                """, parameter_product_and_barcode)

                multi_coupon_count_obj = self._cr.dictfetchall()

                if multi_coupon_count_obj[0]['row_count'] > 0:
                    self._cr.execute("""
                        update multi_coupon
                        set is_reserved = false
                        where product_id = %s
                            and barcode = %s
                    """, parameter_product_and_barcode)
                    self._cr.commit()

                    return_dict = {
                        'status': 'success',
                    }
                else:
                    return_dict = {
                        'status': 'fail',
                        'message': 'Not found coupon.',
                    }
        elif process_type == 'return':
            for product_id in product_ids:
                if not barcode:
                    return {
                        'status': 'fail',
                        'message': 'Api fail',
                    }

                parameter_product_and_barcode = (
                    product_id,
                    barcode
                )

                self._cr.execute("""
                    select count('') as row_count
                    from multi_coupon
                    where is_canceled = false
                        and product_id = %s
                        and barcode = %s
                    limit 1
                """, parameter_product_and_barcode)

                multi_coupon_count_obj = self._cr.dictfetchall()

                if multi_coupon_count_obj[0]['row_count'] > 0:
                    self._cr.execute("""
                        update multi_coupon
                        set is_canceled = true
                        where product_id = %s
                            and barcode = %s
                    """, parameter_product_and_barcode)
                    self._cr.commit()

                    return_dict = {
                        'status': 'success',
                    }
                else:
                    return_dict = {
                        'status': 'fail',
                        'message': 'Not found coupon.',
                    }
        # elif process_type == 'check_limit_coupon':
        #     for product_id in product_ids:
        #         parameter_product = (
        #             product_id
        #         )
        #
        #         self._cr.execute("""
        #             select count('') as row_count
        #             from product_product
        #             where id = %s
        #                   and coupon_limit >= (coupon_used_time + 1)
        #         """, parameter_product)
        #
        #         check_limit_count_obj = self._cr.dictfetchall()
        #
        #         if check_limit_count_obj[0]['row_count'] > 0:
        #             return_dict = {
        #                 'status': 'success',
        #             }
        #         else:
        #             return_dict = {
        #                 'status': 'fail',
        #                 'message': 'This coupon is over limit.',
        #             }
        elif process_type == 'check_multi_coupon':
            if len(product_ids):
                parameter_product_id = ','.join([str(product_id) for product_id in product_ids])
            else:
                parameter_product_id = 'null'

            query_str = """
                select
                    product_id,
                    count(id)
                from
                    (
                    select
                        product_id,
                        id
                    from
                        multi_coupon
                    where
                        is_received is false
                        and is_reserved = false
                        and is_used is false
                        and is_canceled is false
                        and product_id in ({0})
                    order by
                        product_id ) mtc
                group by
                    product_id
            """.format(parameter_product_id)
            self._cr.execute(query_str)

            multi_coupon_id_obj = self._cr.dictfetchall()

            if not len(multi_coupon_id_obj):
                return_dict = {
                    'status': 'fail',
                    'message': 'Not found coupon.',
                }
            else:
                for multi_coupon_id in multi_coupon_id_obj:
                    return_dict[multi_coupon_id['product_id']] = multi_coupon_id['count']
                return_dict['status'] = 'success'
        return return_dict

    @api.model
    def load_product_images(self):
        product_ids = self._context.get('product_ids', False)
        if not product_ids:
            return {
                'status': 'fail',
            }

        result = {}
        for product_id in product_ids:
            product = self.env['product.product'].browse(product_id)
            try:
                if product.image:
                    result[product.id] = product.image
                else:
                    result[product.id] = False
            except Exception, e:
                _logger.error(e)
                result[product.id] = False

        if not len(result):
            return {
                'status': 'fail',
            }
        else:
            result['status'] = 'success'
            return result
