# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import except_orm


class MultiCouponWizard(models.TransientModel):
    _name = 'multi.coupon.wizard'
    _description = "Multi Coupon"

    coupon_prefix = fields.Char(
        string="Prefix",
        required=True,
        size=15,
    )

    quantity = fields.Integer(
        string="Quantity",
        required=True,
    )

    @api.multi
    def action_generate_multi_coupon(self):
        for item in self:
            active_id = item._context['active_id']
            multi_coupon_obj = item.env['multi.coupon']
            running_digit = len(str(abs(item.quantity)))

            parameter_active_id = (
                active_id,
            )

            item._cr.execute("""
                select count('') as count_row
                from multi_coupon
                where is_received is true 
                      and product_id = %s
                limit 1
            """, parameter_active_id)

            count_multi_coupon_obj = item._cr.dictfetchall()

            if count_multi_coupon_obj[0]['count_row'] > 0:
                raise except_orm(_('คูปองถูกใช้แล้ว ไม่สามารถสร้างใหม่ได้'))

            if (running_digit + len(item.coupon_prefix)) > 15:
                raise except_orm(_('ไม่สามารถใช้บาร์โค๊ดเกิน 15 หลักได้'))

            item._cr.execute("""
                delete from multi_coupon
                where product_id = %s
            """, parameter_active_id)

            for running in range(1, item.quantity + 1):
                barcode = item.coupon_prefix + str(running).zfill(running_digit)

                parameter_barcode = (
                    barcode,
                    barcode,
                )

                item._cr.execute("""
                    select (
                            multi_coupon.multi_coupon_count + product_product.product_count
                           ) as count_row
                    from (
                          select count('') as multi_coupon_count
                          from multi_coupon
                          where barcode = %s
                          limit 1
                         ) multi_coupon,
                        (
                         select count('') as product_count
                         from product_product
                         where barcode = %s
                         limit 1
                        ) product_product
                """, parameter_barcode)

                count_barcode_obj = item._cr.dictfetchall()

                if count_barcode_obj[0]['count_row'] > 0:
                    raise except_orm(_('บาร์โค๊ตซ้ำ'))

                multi_coupon_obj.create({
                    'product_id': active_id,
                    'barcode': barcode,
                })

        return {'type': 'ir.actions.act_window_close'}
